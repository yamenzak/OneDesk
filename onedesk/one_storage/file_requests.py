"""Asking somebody for files by name: a file request.

A `Cloud File Request` names the files wanted — *passport copy*, *last three
bank statements* — each required or not, one file or several, of certain
kinds, and whether it **fills a field on a record**. Each person asked gets a
link of their own (`/r/<token>`, `www/r.py`): a checklist with a place to
send each file, which shows what they have sent and takes a replacement
until the request is closed.

**Where a file lands** is decided per item. One asked for a record's field
(an Employee's *Passport*) is attached to the record through that field and
fills it. Any other goes into the request's folder — a folder per person
when several are asked — or, with no folder and a record, onto the record.
Either way it is a File like any other: it has versions, it is in the
explorer, and the request only lists it. A replacement for an item that
takes one file becomes a new version of the file sent before.

The token in a link is kept encrypted and found by its hash, like a
`Cloud Link`'s; a link is somebody's own, so it asks for nothing more. The
person who made the request owns what arrives, and is told as it does.
"""

import os
from urllib.parse import quote

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import add_days, get_fullname, get_url, getdate, now_datetime, today
from werkzeug.exceptions import NotFound
from werkzeug.utils import redirect

from onedesk.one import roles
from onedesk.one_storage import api
from onedesk.one_storage import namespace as ns
from onedesk.one_storage.doctype.cloud_file_request.cloud_file_request import ATTACH, hashed

PREFIX = "@request"

#: Days before the due date a reminder goes, and on the day itself.
REMIND_AT = (3, 1, 0)


def url_of(token: str) -> str:
	return get_url(f"/r/{token}")


def node_id(name: str) -> str:
	return f"{PREFIX}/{name}"


def is_request(node: str | None) -> bool:
	return bool(node) and node.startswith(PREFIX + "/")


# ------------------------------------------------------------ the asker's side


@frappe.whitelist()
@frappe.read_only()
def fields(doctype: str) -> list[dict]:
	"""The attachment fields of a doctype a requested file can fill."""
	if not frappe.has_permission(doctype, "read"):
		return []
	return [
		{"value": one.fieldname, "label": _(one.label or one.fieldname)}
		for one in frappe.get_meta(doctype).fields
		# An image field is often hidden and shown as the record's picture.
		if one.fieldtype in ATTACH and (not one.hidden or one.fieldtype == "Attach Image")
	]


@frappe.whitelist(methods=["POST"])
def make(node: str, values: str | dict) -> dict:
	"""A request for files into `node`: a folder, a record, or neither."""
	values = frappe.parse_json(values) if isinstance(values, str) else values
	if not ns._staff(frappe.session.user):
		frappe.throw(_("Only people on the team can ask for files."), frappe.PermissionError)
	where = _where(node, values.get("title"))
	doc = frappe.get_doc(
		{
			"doctype": "Cloud File Request",
			"title": values.get("title"),
			"message": values.get("message"),
			"due_date": values.get("due_date") or None,
			**where,
			"items": [
				{key: one.get(key) for key in ("label", "description", "required", "several", "accept", "fieldname")}
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
	return [one.strip() for one in (text or "").replace(";", ",").replace("\n", ",").split(",") if one.strip()]


def _where(node: str, title: str | None) -> dict:
	"""Where free files go, from where the request was made."""
	kind = ns.parse(node)
	if kind[0] == ns.RECORDS and len(kind) == 3:
		if not frappe.has_permission(kind[1], "write", kind[2]):
			frappe.throw(_("You may not add files to {0}.").format(kind[2]), frappe.PermissionError)
		return {"reference_doctype": kind[1], "reference_name": kind[2]}
	folder = ns.folder_of(node) if kind[0] in (ns.MY, ns.COMPANY, "file") else None
	if folder:
		api._need(api._item(folder), "add")
		return {"folder": folder}
	# Made from nowhere in particular: a folder of its own in My Files.
	made = api.make_folder(ns.MY, title or _("File request"))
	return {"folder": made["id"]}


def _ask(doc, tokens: dict) -> bool:
	"""Email each new person their link, where the workspace can send mail."""
	from onedesk.one_storage import links

	if not tokens or not links.can_mail():
		return False
	from markupsafe import Markup, escape

	from onedesk.one import notify

	who = get_fullname(doc.owner)
	# The note and the due date are left out, gap and all, when there are none.
	note = Markup("<br><br>") + escape(doc.message) if doc.message else ""
	due = Markup("<br><br>") + escape(_("Due {0}.").format(frappe.format(doc.due_date, "Date"))) if doc.due_date else ""
	for email, token in tokens.items():
		notify.mail("File Request", email, now=False, who=who, request=doc.title, note=note, due=due, link=url_of(token))
	return True


def _mine(name: str):
	doc = frappe.get_doc("Cloud File Request", name)
	user = frappe.session.user
	if doc.owner != user and user != "Administrator" and roles.ADMINISTRATOR not in frappe.get_roles():
		frappe.throw(_("That is no longer here."), frappe.DoesNotExistError)
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
				"where": _("Closed") if row.status == "Closed" else _("{0} of {1} complete").format(done, asked),
			}
		)
	return out


def children(node: str) -> list[dict]:
	"""What has arrived for a request, as the files themselves."""
	doc = _mine(node[len(PREFIX) + 1 :])
	names = [one.file for one in doc.uploads if one.file]
	rows = {one.name: one for one in frappe.get_all("File", filters={"name": ["in", names or [""]]}, fields=ns.FIELDS)}
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
		"items": [{"label": one.label, "required": one.required, "field": one.fieldname} for one in doc.items],
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
	from onedesk.one import notify

	who = get_fullname(doc.owner)
	for person in people:
		notify.mail(
			"File Request Reminder",
			person.email,
			now=False,
			who=who,
			request=doc.title,
			link=url_of(person.get_password("token")),
		)
		frappe.db.set_value("Cloud File Request Recipient", person.name, "last_reminded", today(), update_modified=False)
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
			_remind(doc, [one for one in doc.recipients if one.state != "Complete" and str(one.last_reminded or "") != today()])
		finally:
			frappe.set_user("Administrator")


# ------------------------------------------------------------ the sender's side


def live(token: str | None):
	"""The request and the person a link belongs to, or (None, None)."""
	if not token or len(token) > 64:
		return None, None
	found = frappe.db.get_value(
		"Cloud File Request Recipient", {"token_hash": hashed(token), "parenttype": "Cloud File Request"}, ["parent", "name"], as_dict=True
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
	for one in sent:
		if not accepted(one.filename, wanted.accept):
			return _back(token, "kind")
	owner = doc.owner
	frappe.set_user(owner)
	try:
		was = person.state
		for one in sent:
			_land(doc, person, wanted, one.filename, one.stream.read())
		_settle(doc, person)
		doc.save(ignore_permissions=True)
		_tell(doc, person, wanted, finished=was != "Complete" and person.state == "Complete")
	finally:
		frappe.set_user("Guest")
	return _back(token, "sent")


def _land(doc, person, item, filename: str, content: bytes) -> None:
	"""Put one file where its item says, and write down that it came."""
	from onedesk.one_storage import history, upload

	extension = os.path.splitext(filename)[1].lower()
	name = f"{item.label}{extension}"
	before = next(
		(one for one in doc.uploads if one.email == person.email and one.item == item.label), None
	)
	if item.fieldname:
		node = ns.record_node(doc.reference_doctype, doc.reference_name)
	elif doc.folder:
		node = _their_folder(doc, person)
	else:
		node = ns.record_node(doc.reference_doctype, doc.reference_name)
	placed = upload._place(node, None, {"file_name": name, "content": content})
	if item.fieldname:
		frappe.db.set_value("File", placed["id"], "attached_to_field", item.fieldname)
	if before and not item.several and frappe.db.exists("File", before.file):
		# One file asked for, sent again: a new version of the one before.
		history.replace(ns.row(before.file), placed["id"])
		kept = before.file
		before.sent_on = now_datetime()
	else:
		kept = placed["id"]
		doc.append("uploads", {"email": person.email, "item": item.label, "file": kept, "sent_on": now_datetime()})
	if item.fieldname:
		url = frappe.db.get_value("File", kept, "file_url")
		frappe.db.set_value(doc.reference_doctype, doc.reference_name, item.fieldname, url)


def _their_folder(doc, person) -> str:
	"""The request's folder, or a folder in it for this person when several
	were asked."""
	if len(doc.recipients) < 2:
		return doc.folder
	found = frappe.db.get_value(
		"File", {"folder": doc.folder, "is_folder": 1, "file_name": person.email, "one_deleted": 0}, "name"
	)
	return found or api.make_folder(doc.folder, person.email)["id"]


def _settle(doc, person) -> None:
	have = {one.item for one in doc.uploads if one.email == person.email}
	# With nothing marked required, every item is.
	required = [one.label for one in doc.items if one.required] or [one.label for one in doc.items]
	if all(label in have for label in required):
		person.state = "Complete"
	elif have:
		person.state = "Partly Sent"
	person.last_sent = now_datetime()


def _tell(doc, person, item, finished: bool) -> None:
	"""The owner hears of each item sent, and once when a person has sent all of them."""
	from onedesk.one import notify

	notify.notify(
		"File Request Complete" if finished else "File Request Answered",
		doc.owner,
		record=("Cloud File Request", doc.name),
		link=f"/desk/onecloud?node={quote(node_id(doc.name), safe='')}",
		sender=person.email,
		request=doc.title,
		item=item.label,
	)


def _back(token: str, said: str | None = None):
	return redirect(f"/r/{token}" + (f"?said={said}" if said else ""), 303)


def overdue(doc) -> bool:
	return bool(doc.due_date and getdate(doc.due_date) < getdate(today()))
