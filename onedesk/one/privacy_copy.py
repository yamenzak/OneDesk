"""A copy of a person's data, reviewed by an administrator before it goes.
See one/privacy.py for deletion, and README "Privacy Requests".

Frappe's `get_user_data` hands over every row a person's address appears in,
whole: mail they were copied on, records they deleted, pages they printed,
other people's values in the changes they made. Much of that is the
workspace's, not theirs. GDPR article 15 gives a person a copy of their
personal data, and 15(4) lets it be limited where it would harm the rights
of others, the company's confidential information among them. So:

- what is plainly about the person always goes: their account and profile,
  sign-ins, contacts with their address, what OneAI remembers about them,
  what they agreed to;
- what they wrote or touched goes unless an administrator withholds it, kind
  by kind, with a reason the person is told: mail, comments, to-dos, their
  OneAI conversations, which records they changed (never the values), what
  they exported or printed (never the pages), their notifications;
- what is never theirs to take never goes: the contents of records they
  deleted, printed pages, values in other people's records, account secrets.

The request is a `Personal Data Download Request`, frappe's own, with three
custom fields for where it stands, what was withheld and who decided.
"""

import json

import frappe
from frappe import _, _lt
from frappe.utils import now_datetime

from onedesk.one import roles

DOWNLOAD = "Personal Data Download Request"

#: The kinds a copy is made of, in the order it reads: (key, label, always).
#: An administrator may withhold any kind that is not always given.
KINDS = (
	("account", _lt("Your account and profile"), True),
	("signins", _lt("Your sign-ins"), True),
	("contacts", _lt("Contacts and addresses with your address"), True),
	("records", _lt("Leads, deals, customers, suppliers and applications with your address"), True),
	("memory", _lt("What OneAI remembers about you"), True),
	("agreements", _lt("What you agreed to"), True),
	("mail", _lt("Mail you sent or received"), False),
	("comments", _lt("Comments you wrote"), False),
	("todos", _lt("To-dos given to you"), False),
	("oneai", _lt("Your conversations with OneAI"), False),
	("changes", _lt("Records you changed, without the values"), False),
	("exports", _lt("What you exported or printed, without the pages"), False),
	("notifications", _lt("Notifications you got"), False),
)

#: What a copy holds for somebody who is not a user: a customer's contact, a
#: supplier, a lead, an applicant. The rest is about an account they do not have.
OUTSIDER = ("contacts", "records", "mail")

#: Records that name somebody by their address, as (doctype, field, fields shown).
RECORDS = (
	("Lead", "email_id", ["lead_name", "company_name", "status", "source", "creation"]),
	("Opportunity", "contact_email", ["opportunity_from", "party_name", "status", "creation"]),
	("Customer", "email_id", ["customer_name", "customer_group", "creation"]),
	("Supplier", "email_id", ["supplier_name", "supplier_group", "creation"]),
	("Job Applicant", "email_id", ["applicant_name", "job_title", "status", "creation"]),
)

#: What never goes, said in the copy so the person knows it exists.
NEVER = (
	"The contents of records you deleted",
	"Pages you printed",
	"Values in records you changed, which are the workspace's",
	"Account secrets such as reset keys",
)

#: The same, for somebody who is not a user.
NEVER_OUTSIDER = ("The rest of the records that name you, which are the workspace's",)

#: The account's own fields that are about the person; never its keys.
ACCOUNT = (
	"email",
	"first_name",
	"last_name",
	"full_name",
	"gender",
	"birth_date",
	"phone",
	"mobile_no",
	"location",
	"bio",
	"language",
	"time_zone",
	"creation",
	"last_login",
	"last_active",
)


def _rows(doctype: str, filters, fields: list, order_by: str = "creation desc") -> list[dict]:
	if not frappe.db.exists("DocType", doctype):
		return []
	return [dict(one) for one in frappe.get_all(doctype, filters=filters, fields=fields, order_by=order_by)]


def _mail_filters(user: str) -> list:
	return [["Communication", "communication_type", "=", "Communication"]], [
		["Communication", "sender", "like", f"%{user}%"],
		["Communication", "recipients", "like", f"%{user}%"],
		["Communication", "cc", "like", f"%{user}%"],
	]


def gather_kind(key: str, user: str):
	"""One kind of the copy, for one person. Read past permissions: the only
	filter is the person's own address."""
	if key == "account":
		account = frappe.db.get_value("User", user, list(ACCOUNT), as_dict=True) or {}
		account["roles"] = frappe.get_roles(user)
		employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
		if employee:
			from onedesk.one import settings

			fields = (
				"employee_name",
				"date_of_birth",
				"gender",
				"date_of_joining",
				"designation",
				"department",
			)
			fields += tuple(settings.EMPLOYEE_OWN) + tuple(settings.SHARED.values())
			meta = frappe.get_meta("Employee")
			wanted = [one for one in dict.fromkeys(fields) if meta.get_field(one)]
			account["employee"] = frappe.db.get_value("Employee", employee, wanted, as_dict=True)
		return account
	if key == "signins":
		return _rows("Activity Log", {"user": user}, ["operation", "status", "ip_address", "creation"])
	if key == "contacts":
		names = {
			one.parent
			for one in frappe.get_all("Contact Email", filters={"email_id": user}, fields=["parent"])
		}
		return {
			"contacts": _rows(
				"Contact",
				{"name": ["in", list(names) or [""]]},
				["first_name", "last_name", "email_id", "phone", "mobile_no", "company_name", "designation"],
			),
			"addresses": _rows(
				"Address",
				{"email_id": user},
				[
					"address_title",
					"address_line1",
					"address_line2",
					"city",
					"state",
					"pincode",
					"country",
					"phone",
				],
			),
		}
	if key == "records":
		said = {}
		for doctype, field, fields in RECORDS:
			if not frappe.db.exists("DocType", doctype):
				continue
			meta = frappe.get_meta(doctype)
			if not meta.get_field(field):
				continue
			rows = _rows(
				doctype, {field: user}, [one for one in fields if one == "creation" or meta.get_field(one)]
			)
			if rows:
				said[doctype] = rows
		return said
	if key == "memory":
		return _rows("AI Memory", {"owner": user}, ["fact", "about_doctype", "about_name", "creation"])
	if key == "agreements":
		return _rows("Legal Acceptance", {"user": user}, ["document", "version", "accepted_on", "address"])
	if key == "mail":
		filters, either = _mail_filters(user)
		return [
			dict(one)
			for one in frappe.get_all(
				"Communication",
				filters=filters,
				or_filters=either,
				fields=[
					"subject",
					"communication_date",
					"sent_or_received",
					"sender",
					"recipients",
					"cc",
					"content",
				],
				order_by="communication_date desc",
			)
		]
	if key == "comments":
		return _rows(
			"Comment",
			{"owner": user, "comment_type": "Comment"},
			["reference_doctype", "reference_name", "content", "creation"],
		)
	if key == "todos":
		return _rows(
			"ToDo",
			{"allocated_to": user},
			["description", "status", "date", "reference_type", "reference_name", "creation"],
		)
	if key == "oneai":
		return _rows("AI Chat", {"owner": user}, ["title", "last_said_on", "turns"])
	if key == "changes":
		said = []
		for one in _rows("Version", {"owner": user}, ["ref_doctype", "docname", "data", "creation"]):
			data = frappe.parse_json(one.pop("data") or "{}") or {}
			meta = (
				frappe.get_meta(one["ref_doctype"])
				if frappe.db.exists("DocType", one["ref_doctype"])
				else None
			)
			label = (lambda field: meta.get_label(field)) if meta else (lambda field: field)
			one["fields"] = [label(change[0]) for change in data.get("changed") or []]
			one["rows_added"] = len(data.get("added") or [])
			one["rows_removed"] = len(data.get("removed") or [])
			said.append(one)
		return said
	if key == "exports":
		return _rows(
			"Access Log",
			{"user": user},
			["export_from", "reference_document", "report_name", "file_type", "creation"],
		)
	if key == "notifications":
		return _rows(
			"Notification Log",
			{"for_user": user},
			["subject", "document_type", "document_name", "creation"],
		)
	raise KeyError(key)


def kinds_for(address: str) -> tuple:
	"""The kinds a copy has: all of them for a user, fewer for somebody who is
	not one."""
	if frappe.db.exists("User", address):
		return KINDS
	return tuple(one for one in KINDS if one[0] in OUTSIDER)


def counts(user: str) -> list[dict]:
	"""Each kind with how much of it there is: what the administrator reviews."""
	out = []
	for key, label, always in kinds_for(user):
		found = gather_kind(key, user)
		size = len(found) if isinstance(found, list) else 1 if found else 0
		if key == "contacts":
			size = len(found["contacts"]) + len(found["addresses"])
		if key == "records":
			size = sum(len(rows) for rows in found.values())
		out.append({"key": key, "label": str(label), "always": always, "count": size})
	return out


# ------------------------------------------------------------------ the flow


def _file_of(user: str, request: str) -> dict:
	"""Where a copy's file is: on the person's own account, which they may
	read, rather than on the request, which only administrators may."""
	return {
		"attached_to_doctype": "User",
		"attached_to_name": user,
		"file_name": ["like", f"Personal-Data-%-{request}.json"],
	}


def last(user: str) -> dict | None:
	"""The person's last request, as the Profile page shows it."""
	found = frappe.get_all(
		DOWNLOAD,
		filters={"user": user},
		fields=["name", "creation", "one_status", "one_withheld"],
		order_by="creation desc",
		limit=1,
	)
	if not found:
		return None
	one = found[0]
	url = frappe.db.get_value("File", _file_of(user, one.name), "file_url")
	return {
		"on": one.creation,
		"status": one.one_status or ("Ready" if url else "Waiting"),
		"withheld": one.one_withheld,
		"url": url,
		"ready": bool(url),
	}


@frappe.whitelist(methods=["POST"])
def ask() -> dict:
	"""A copy asked for by the person, for an administrator to review."""
	from onedesk.one import notify, privacy

	user = privacy._mine()
	if frappe.db.exists(DOWNLOAD, {"user": user, "one_status": ["in", ["Waiting", "Gathering"]]}):
		frappe.throw(_("You have asked already; an administrator is reviewing it."))
	# frappe's insert would gather everything at once and mail its own message.
	doc = frappe.get_doc(
		{
			"doctype": DOWNLOAD,
			"user": user,
			"user_name": frappe.utils.get_fullname(user),
			"one_email": user,
			"one_status": "Waiting",
		}
	)
	doc.set_new_name()
	doc.set_user_and_timestamp()
	doc.db_insert()
	notify.notify(
		"Copy Asked",
		privacy._administrators(),
		record=(DOWNLOAD, doc.name),
		person=frappe.utils.get_fullname(user),
	)
	return privacy.state(user)


@frappe.whitelist()
def review(name: str) -> dict:
	"""What a request would give, kind by kind, for the administrator to
	decide what goes."""
	roles.require()
	doc = frappe.get_doc(DOWNLOAD, name)
	address = doc.user or doc.one_email
	return {"person": doc.user_name or address, "status": doc.one_status, "kinds": counts(address)}


@frappe.whitelist(methods=["POST"])
def send(name: str, withheld: str | list | None = None, why: str | None = None) -> None:
	"""Approved: everything but what the administrator withheld, for the
	reason they give, which the person is told."""
	roles.require()
	doc = frappe.get_doc(DOWNLOAD, name)
	if doc.one_status != "Waiting":
		frappe.throw(_("This request is not waiting for a decision."))
	withheld = [one for one in (frappe.parse_json(withheld) or []) if one]
	optional = {key for key, _label, always in kinds_for(doc.user or doc.one_email) if not always}
	if set(withheld) - optional:
		frappe.throw(
			_("Only what the person wrote or touched can be withheld; what is about them always goes.")
		)
	why = (why or "").strip()
	if withheld and not why:
		frappe.throw(_("Say why it is withheld, so they know."))
	labels = {key: str(label) for key, label, _always in KINDS}
	said = f"{', '.join(labels[one] for one in withheld)}: {why}" if withheld else ""
	doc.db_set(
		{"one_status": "Gathering", "one_withheld": said, "one_decided_by": frappe.session.user},
		update_modified=False,
	)
	doc.add_comment("Info", _("Approved by {0}").format(frappe.utils.get_fullname()))
	frappe.enqueue(gather, queue="short", request=name, withheld=withheld, enqueue_after_commit=True)


def gather(request: str, withheld: list | None = None) -> None:
	"""The copy, as reviewed. A user's is a file only they may open, kept on
	their account and announced on their bell; somebody who is not a user is
	mailed a link to download it that works for a week (one/privacy_public.py)."""
	from onedesk.one import notify

	doc = frappe.get_doc(DOWNLOAD, request)
	address = doc.user or doc.one_email
	withheld = set(withheld or [])
	copy = {
		"person": doc.user_name or address,
		"address": address,
		"asked_on": str(doc.creation),
		"given_on": str(now_datetime()),
		"workspace": frappe.utils.get_url(),
	}
	# What is kept is "<labels>: <why>"; under each label, only the why.
	why = (doc.one_withheld or "").partition(": ")[2]
	for key, label, _always in kinds_for(address):
		copy[str(label)] = gather_kind(key, address) if key not in withheld else f"Withheld: {why}"
	copy["Never included"] = list(NEVER if doc.user else NEVER_OUTSIDER)
	where = _file_of(address, doc.name) if doc.user else _outsider_file(doc.name)
	# Gathered again, it replaces the copy before it.
	for old in frappe.get_all("File", filters=where, pluck="name"):
		frappe.delete_doc("File", old, ignore_permissions=True)
	file = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"Personal-Data-{(doc.user_name or 'copy').replace(' ', '-')}-{doc.name}.json",
			"attached_to_doctype": "User" if doc.user else DOWNLOAD,
			"attached_to_name": doc.user or doc.name,
			"content": json.dumps(copy, indent=2, default=str, ensure_ascii=False),
			"is_private": 1,
		}
	)
	file.flags.skip_file_size_check = True
	file.save(ignore_permissions=True)
	withheld_said = doc.one_withheld or _("Nothing was withheld.")
	if not doc.user:
		from onedesk.one import privacy_public

		frappe.db.set_value(DOWNLOAD, doc.name, "one_status", "Ready", update_modified=False)
		notify.mail(
			"Your Data Is Ready to Download",
			address,
			url=privacy_public.download_link(doc.name),
			days=privacy_public.DOWNLOAD_DAYS,
			withheld=withheld_said,
		)
		return
	frappe.db.set_value("File", file.name, "owner", doc.user, update_modified=False)
	frappe.db.set_value(DOWNLOAD, doc.name, {"owner": doc.user, "one_status": "Ready"}, update_modified=False)
	notify.notify(
		"Your Data Is Ready",
		doc.user,
		link="/desk/settings?section=profile",
		withheld=withheld_said,
	)
	frappe.publish_realtime("one_privacy", user=doc.user)


def _outsider_file(request: str) -> dict:
	"""A copy for somebody who is not a user: on the request, which only
	administrators may open; they download it through a signed link."""
	return {
		"attached_to_doctype": DOWNLOAD,
		"attached_to_name": request,
		"file_name": ["like", "Personal-Data-%"],
	}


# ------------------------------------------------------------------ guards


def query(user: str | None = None) -> str | None:
	"""permission_query_conditions: the administrators'."""
	user = user or frappe.session.user
	if user == "Administrator" or roles.administers(user):
		return None
	return "1=0"


def has_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
	"""Read only, and the administrators': decided through `send`, never by
	editing the record. The person sees theirs on their profile."""
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	return ptype in ("read", "report", None) and roles.administers(user)
