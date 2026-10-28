"""Asking somebody for files by name: a file request.

Each person asked gets a link of their own (`/r/<token>`, `www/r.py`), a
checklist with a place to send each file."""

import io
import os

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import add_days, get_fullname, get_url, getdate, now_datetime, today
from werkzeug.exceptions import NotFound
from werkzeug.utils import redirect

from onedesk.one import roles
from onedesk.one_storage import api, targets, tell
from onedesk.one_storage import namespace as ns
from onedesk.one_storage.doctype.cloud_file_request.cloud_file_request import hashed

PREFIX = "@request"

REMIND_AT = (3, 1, 0)


def url_of(token: str) -> str:
	return get_url(f"/r/{token}")


def node_id(name: str) -> str:
	return f"{PREFIX}/{name}"


def is_request(node: str | None) -> bool:
	return bool(node) and node.startswith(PREFIX + "/")


@frappe.whitelist()
@frappe.read_only()
def fields(doctype: str) -> list[dict]:
	"""Where on a record of this kind a requested file can go, as one list
	(targets.choices)."""
	if not frappe.has_permission(doctype, "read"):
		return []
	return targets.choices(doctype)


@frappe.whitelist()
@frappe.read_only()
def asked_at(doctype: str, name: str) -> str:
	"""The address to ask a record for files at: the user it is, else its
	first email address."""
	if not frappe.has_permission(doctype, "read", name):
		return ""
	doc = frappe.get_doc(doctype, name)
	user = next((one for one in doc.meta.fields if one.fieldtype == "Link" and one.options == "User" and one.fieldname == "user_id"), None)
	if user and doc.get(user.fieldname):
		return doc.get(user.fieldname)
	return next((doc.get(one.fieldname) for one in doc.meta.fields if one.options == "Email" and doc.get(one.fieldname)), "")


@frappe.whitelist(methods=["POST"])
def make(node: str, values: str | dict) -> dict:
	"""A request for files into `node`: a folder, a record, or neither."""
	values = frappe.parse_json(values) if isinstance(values, str) else values
	if not ns._staff(frappe.session.user):
		frappe.throw(_("Only people on the team can request files."), frappe.PermissionError)
	where = _where(node, values.get("title"))
	doc = frappe.get_doc(
		{
			"doctype": "Cloud File Request",
			"title": values.get("title"),
			"message": values.get("message"),
			"due_date": values.get("due_date") or None,
			**where,
			"items": [
				{
					key: one.get(key)
					for key in ("label", "description", "required", "several", "accept", "fieldname", "row_key")
				}
				for one in values.get("items") or []
				if one.get("label")
			],
			"recipients": [{"email": email} for email in _emails(values.get("recipients"))],
		}
	)
	doc.insert(ignore_permissions=True)
	tokens = doc.flags.tokens or {}
	mailed = _ask(doc, tokens)
	return {
		"name": doc.name,
		"node": node_id(doc.name),
		"mailed": mailed,
		"links": [{"email": email, "url": url_of(token)} for email, token in tokens.items()],
	}


def _emails(text) -> list[str]:
	if isinstance(text, list):
		return [one.strip() for one in text if one and one.strip()]
	return [
		one.strip() for one in (text or "").replace(";", ",").replace("\n", ",").split(",") if one.strip()
	]


def _where(node: str, title: str | None) -> dict:
	"""Where free files go, from where the request was made. Asked from a
	project's Featured Media, they go to the project, to be featured by hand."""
	kind = ns.parse(node)
	if kind[0] == "featured":
		kind = (ns.RECORDS, "Project", kind[1])
	if kind[0] == ns.RECORDS and len(kind) == 3:
		if not frappe.has_permission(kind[1], "write", kind[2]):
			frappe.throw(_("You can't add files to {0}.").format(kind[2]), frappe.PermissionError)
		return {"reference_doctype": kind[1], "reference_name": kind[2]}
	folder = ns.folder_of(node) if kind[0] in (ns.MY, ns.COMPANY, "file") else None
	if folder:
		api._need(api._item(folder), "add")
	made = api.make_folder(folder or ns.MY, title or _("File request"))
	return {"folder": made["id"]}


def _ask(doc, tokens: dict) -> bool:
	"""Email each new person their link, where the workspace can send mail."""
	from onedesk.one_storage import links

	if not tokens or not links.can_mail():
		return False
	tell.files_requested(doc, tokens)
	return True


def _mine(name: str):
	doc = frappe.get_doc("Cloud File Request", name)
	user = frappe.session.user
	if doc.owner != user and user != "Administrator" and roles.ADMINISTRATOR not in frappe.get_roles():
		frappe.throw(_("This item no longer exists."), frappe.DoesNotExistError)
	return doc


def visible() -> list[dict]:
	"""Requests: the ones the reader made, newest first."""
	rows = frappe.get_all(
		"Cloud File Request",
		filters={"owner": frappe.session.user},
		fields=["name", "title", "status", "modified", "due_date"],
		order_by="creation desc",
		limit=500,
	)
	states = {}
	for one in frappe.get_all(
		"Cloud File Request Recipient",
		filters={"parent": ["in", [row.name for row in rows] or [""]], "parenttype": "Cloud File Request"},
		fields=["parent", "state"],
	):
		states.setdefault(one.parent, []).append(one.state)
	out = []
	for row in rows:
		done = sum(1 for state in states.get(row.name, []) if state == "Complete")
		asked = len(states.get(row.name, []))
		out.append(
			{
				"id": node_id(row.name),
				"name": row.title,
				"folder": True,
				"virtual": True,
				"request": True,
				"icon": "inbox",
				"modified": row.modified,
				"where": _("Closed")
				if row.status == "Closed"
				else _("{0} of {1} complete").format(done, asked),
			}
		)
	return out


def children(node: str) -> list[dict]:
	"""What has arrived for a request, as the files themselves."""
	doc = _mine(node[len(PREFIX) + 1 :])
	names = [one.file for one in doc.uploads if one.file]
	rows = {
		one.name: one
		for one in frappe.get_all("File", filters={"name": ["in", names or [""]]}, fields=ns.FIELDS)
	}
	out = []
	for one in doc.uploads:
		if one.file in rows:
			out.append({**ns.node(rows[one.file]), "where": f"{one.item} · {one.email}"})
	return out


def trail(node: str) -> list[dict]:
	title = frappe.db.get_value("Cloud File Request", node[len(PREFIX) + 1 :], "title") or node
	return [
		{"id": ns.ROOT, "name": _("OneCloud")},
		{"id": ns.REQUESTS, "name": _("Requests")},
		{"id": node, "name": title},
	]


@frappe.whitelist()
@frappe.read_only()
def progress(name: str) -> dict:
	"""Who has sent what, item by item, with each person's link."""
	doc = _mine(name)
	sent = {}
	for one in doc.uploads:
		sent.setdefault((one.email, one.item), []).append(
			frappe.db.get_value("File", one.file, "file_name") or one.file
		)
	return {
		"title": doc.title,
		"status": doc.status,
		"due_date": doc.due_date,
		"items": [
			{"label": one.label, "required": one.required, "field": one.fieldname} for one in doc.items
		],
		"people": [
			{
				"email": person.email,
				"state": person.state,
				"url": url_of(person.get_password("token")),
				"sent": {one.label: sent.get((person.email, one.label), []) for one in doc.items},
			}
			for person in doc.recipients
		],
	}


@frappe.whitelist(methods=["POST"])
def remind(name: str) -> int:
	doc = _mine(name)
	return _remind(doc, [one for one in doc.recipients if one.state != "Complete"])


@frappe.whitelist(methods=["POST"])
def close(name: str, closed: int = 1) -> None:
	doc = _mine(name)
	doc.db_set("status", "Closed" if int(closed) else "Open")


def _remind(doc, people) -> int:
	from onedesk.one_storage import links

	if not people or not links.can_mail():
		return 0
	who = get_fullname(doc.owner)
	for person in people:
		tell.reminded(doc, person, who)
		frappe.db.set_value(
			"Cloud File Request Recipient", person.name, "last_reminded", today(), update_modified=False
		)
	return len(people)


def remind_due() -> None:
	"""Daily: a reminder three days before the due date, the day before, and on
	the day, to whoever has not sent everything required."""
	wanted = [add_days(today(), days) for days in REMIND_AT]
	for name in frappe.get_all(
		"Cloud File Request", filters={"status": "Open", "due_date": ["in", wanted]}, pluck="name"
	):
		doc = frappe.get_doc("Cloud File Request", name)
		frappe.set_user(doc.owner)
		try:
			_remind(
				doc,
				[
					one
					for one in doc.recipients
					if one.state != "Complete" and str(one.last_reminded or "") != today()
				],
			)
		finally:
			frappe.set_user("Administrator")


def live(token: str | None):
	"""The request and the person a link belongs to, or (None, None)."""
	if not token or len(token) > 64:
		return None, None
	found = frappe.db.get_value(
		"Cloud File Request Recipient",
		{"token_hash": hashed(token), "parenttype": "Cloud File Request"},
		["parent", "name"],
		as_dict=True,
	)
	if not found:
		return None, None
	doc = frappe.get_doc("Cloud File Request", found.parent)
	person = next((one for one in doc.recipients if one.name == found.name), None)
	return doc, person


def accepted(name: str, accept: str | None) -> bool:
	"""Whether a file's name is one of the kinds an item asks for. Pure."""
	kinds = [one.strip() for one in (accept or "").split(",") if one.strip()]
	return not kinds or os.path.splitext(name or "")[1].lower().lstrip(".") in kinds


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=120, seconds=60 * 60)
def send(token: str, item: str):
	"""Files sent for one item of a request."""
	doc, person = live(token)
	if not doc:
		raise NotFound
	if doc.status != "Open":
		return _back(token, "closed")
	wanted = next((one for one in doc.items if one.name == item), None)
	if not wanted:
		raise NotFound
	sent = [one for one in frappe.request.files.getlist("file") if one and one.filename]
	if not sent:
		return _back(token, "nothing")
	if not wanted.several:
		sent = sent[:1]
	if not all(accepted(one.filename, wanted.accept) for one in sent):
		return _back(token, "kind")
	given = {key[2:]: value for key, value in frappe.form_dict.items() if key.startswith("v_")}
	try:
		_receive(doc, person, wanted, sent, given)
	except frappe.ValidationError:
		frappe.clear_messages()
		return _back(token, "details")
	finally:
		frappe.set_user("Guest")
	return _back(token, "sent")


@frappe.whitelist(methods=["POST"])
def send_mine(request: str, item: str, file_url: str, values: str | None = None) -> None:
	"""A file sent for one item of a request asked of the signed-in person,
	from One rather than the link (Home's Asked of You). It comes as frappe's
	own upload does, already a File; it is put in place as a copy and the
	upload, nobody's yet, goes."""
	doc, person, wanted = _asked_of_me(request, item)
	if doc.status != "Open":
		frappe.throw(_("This request is closed."))
	upload = _uploaded(file_url)
	if not accepted(upload.file_name, wanted.accept):
		frappe.throw(_("{0} takes only {1}.").format(wanted.label, wanted.accept))
	user = frappe.session.user
	try:
		_receive(doc, person, wanted, [_Sent(upload.file_name, upload.get_content())], frappe.parse_json(values) if values else {})
	finally:
		frappe.set_user(user)
	if upload.owner == user and not upload.attached_to_name:
		frappe.delete_doc("File", upload.name, ignore_permissions=True)


class _Sent:
	"""A file in hand as `_receive` takes it: a name and its bytes."""

	def __init__(self, filename: str, content: bytes):
		self.filename = filename
		self.stream = io.BytesIO(content if isinstance(content, bytes) else content.encode())


def _uploaded(file_url: str):
	"""The File the signed-in person just uploaded or picked, by its address."""
	for name in frappe.get_all("File", filters={"file_url": file_url, "is_folder": 0}, pluck="name", order_by="creation desc"):
		one = frappe.get_doc("File", name)
		if one.owner == frappe.session.user or ns.may(one.as_dict()):
			return one
	frappe.throw(_("Choose a file to send."))


def _asked_of_me(request: str, item: str):
	from onedesk.one_hr import own

	doc = frappe.get_doc("Cloud File Request", request)
	mine = own.addresses_of()
	person = next((one for one in doc.recipients if one.email in mine), None)
	wanted = next((one for one in doc.items if one.name == item), None)
	if not person or not wanted:
		raise NotFound
	return doc, person, wanted


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=30, seconds=60 * 60)
def guess(item: str, token: str | None = None, request: str | None = None, file_url: str | None = None) -> dict:
	"""What OneAI reads off a file about to be sent for the item's asked
	columns (targets.asked), for the sender to check: by the link's token,
	or as the signed-in person. Nothing is kept; nothing when reading is off."""
	from onedesk.one import apps

	if token:
		doc, _person = live(token)
		wanted = next((one for one in doc.items if one.name == item), None) if doc else None
	else:
		doc, _person, wanted = _asked_of_me(request, item)
	if not wanted or not apps.intake_on():
		return {}
	if file_url and not token:
		upload = _uploaded(file_url)
		sent = _Sent(upload.file_name, upload.get_content())
	else:
		sent = next((one for one in frappe.request.files.getlist("file") if one and one.filename), None)
	fields = _asked(doc, wanted)
	if not sent or not fields:
		return {}
	from onedesk.one_ai.reading import fill

	user = frappe.session.user
	frappe.set_user(doc.owner)
	try:
		return fill.from_file(_child(doc, wanted), fields, sent.filename, sent.stream.read(), {"kind": wanted.row_key}, doc.name)
	finally:
		frappe.set_user(user)


def _receive(doc, person, wanted, sent, given: dict | None = None) -> None:
	"""Each file sent for an item put where it goes, as the person who asked,
	and the request brought up to date."""
	values = targets.clean(_asked(doc, wanted), given)
	frappe.set_user(doc.owner)
	was = person.state
	for one in sent:
		_land(doc, person, wanted, one.filename, one.stream.read(), values)
	_settle(doc, person)
	doc.save(ignore_permissions=True)
	tell.request_answered(doc, person, wanted, finished=was != "Complete" and person.state == "Complete")


def _asked(doc, item) -> list[dict]:
	"""The columns asked with an item's file (targets.asked)."""
	return targets.asked(doc.reference_doctype, item.fieldname) if item.fieldname else []


def _child(doc, item) -> str:
	table, _field = targets.split(item.fieldname)
	return frappe.get_meta(doc.reference_doctype).get_field(table).options


def asked_of(addresses: list[str]) -> list[dict]:
	"""The open requests still waiting on these addresses, each with what it
	asks for, what it asks with each file, and what has come, soonest due
	first, for Home's Asked of You."""
	if not addresses:
		return []
	asked = frappe.get_all(
		"Cloud File Request Recipient",
		filters={"email": ["in", addresses], "parenttype": "Cloud File Request", "state": ["!=", "Complete"]},
		fields=["parent", "email"],
	)
	out = []
	for one in asked:
		doc = frappe.get_doc("Cloud File Request", one.parent)
		if doc.status != "Open":
			continue
		have = {row.item for row in doc.uploads if row.email == one.email}
		out.append(
			{
				"name": doc.name,
				"title": doc.title,
				"by": get_fullname(doc.owner),
				"due_date": doc.due_date,
				"overdue": overdue(doc),
				"message": doc.message,
				"items": [
					{
						"name": row.name,
						"label": row.label,
						"description": row.description,
						"required": row.required,
						"several": row.several,
						"accept": row.accept,
						"asked": _asked(doc, row),
						"sent": row.label in have,
					}
					for row in doc.items
				],
			}
		)
	return sorted(out, key=lambda one: str(one["due_date"] or "9999"))


def _land(doc, person, item, filename: str, content: bytes, values: dict) -> None:
	"""Put one file where its item says and write down that it came."""
	from onedesk.one_storage import history, upload

	extension = os.path.splitext(filename)[1].lower()
	name = f"{item.label}{extension}"
	before = next((one for one in doc.uploads if one.email == person.email and one.item == item.label), None)
	if item.fieldname:
		node = ns.record_node(doc.reference_doctype, doc.reference_name)
	elif doc.folder:
		node = _their_folder(doc, person)
	else:
		node = ns.record_node(doc.reference_doctype, doc.reference_name)
	placed = upload._place(node, None, {"file_name": name, "content": content})
	if item.fieldname and "." not in item.fieldname:
		frappe.db.set_value("File", placed["id"], "attached_to_field", item.fieldname)
	if before and not item.several and frappe.db.exists("File", before.file):
		history.replace(ns.row(before.file), placed["id"])
		kept = before.file
		before.sent_on = now_datetime()
	else:
		kept = placed["id"]
		doc.append(
			"uploads", {"email": person.email, "item": item.label, "file": kept, "sent_on": now_datetime()}
		)
	if item.fieldname:
		url = frappe.db.get_value("File", kept, "file_url")
		targets.put(doc.reference_doctype, doc.reference_name, item.fieldname, item.row_key, url, values)


def _their_folder(doc, person) -> str:
	"""The request's folder, or a folder in it for this person when several
	were asked, named as the workspace knows them."""
	if len(doc.recipients) < 2:
		return doc.folder
	called = _called(person.email)
	for name in {called, person.email}:
		found = frappe.db.get_value(
			"File", {"folder": doc.folder, "is_folder": 1, "file_name": name, "one_deleted": 0}, "name"
		)
		if found:
			return found
	return api.make_folder(doc.folder, called)["id"]


def _called(email: str) -> str:
	"""A sender's name: their contact's, or the user's, or else their address."""
	contact = frappe.db.get_value("Contact Email", {"email_id": email, "parenttype": "Contact"}, "parent")
	if contact:
		name = frappe.db.get_value("Contact", contact, "full_name")
		if name and name.strip():
			return name.strip()
	name = frappe.db.get_value("User", {"email": email}, "full_name")
	return (name or "").strip() or email


def _settle(doc, person) -> None:
	have = {one.item for one in doc.uploads if one.email == person.email}
	required = [one.label for one in doc.items if one.required] or [one.label for one in doc.items]
	if all(label in have for label in required):
		person.state = "Complete"
	elif have:
		person.state = "Partly Sent"
	person.last_sent = now_datetime()


def _back(token: str, said: str | None = None):
	return redirect(f"/r/{token}" + (f"?said={said}" if said else ""), 303)


def overdue(doc) -> bool:
	return bool(doc.due_date and getdate(doc.due_date) < getdate(today()))
