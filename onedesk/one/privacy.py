"""Privacy Requests: a copy of your data, and your account deleted.
docs/DESK-COVERAGE.md, P2.

Frappe has both: a `Personal Data Download Request` that gathers what a person
left across the workspace (the `user_data_fields` hooks) into one file, and a
`Personal Data Deletion Request` that redacts their name and address from
those records, disables the account and renames it to an anonymous one. Both
are driven by its System Manager and its own mails ("Dear User"), and nobody
on a workspace is either. Here:

- anybody asks from You > Profile: a copy of their data, which arrives on
  their bell and by mail; or their account deleted, confirmed with their
  password, because it cannot be undone;
- a workspace administrator decides on a deletion under Workspace > Privacy
  Requests: approve it, or hold it with a reason the person is told (an open
  payroll, a dispute: what the law makes the workspace keep);
- approving runs frappe's own erasure, as frappe runs it, after One deletes
  what is only the person's and no use to anybody else: their OneAI
  conversations and memories, notifications, devices and feeds;
- what the workspace keeps is kept with the name and address replaced:
  invoices they raised, tasks they did, the Recycle Bin and the Audit Log.
  An employee record is HR's, kept as the law requires, and deleted by HR.

Nobody deletes the last administrator, or the person the workspace is billed
to: both have to be handed to somebody else first.
"""

import frappe
from frappe import _
from frappe.utils import add_to_date, now_datetime
from frappe.website.doctype.personal_data_download_request.personal_data_download_request import (
	get_user_data,
)

from onedesk.one import roles

DOWNLOAD = "Personal Data Download Request"
DELETION = "Personal Data Deletion Request"

GRANTS = {DELETION: ("read", "report")}

#: What is only the person's and of no use to the workspace once they are
#: gone: deleted outright before frappe's erasure, as {doctype: field}.
ONLY_THEIRS = {
	"AI Chat": "owner",
	"AI Memory": "owner",
	"Notification Log": "for_user",
	"Push Device": "user",
	"Calendar Feed": "user",
	"Cloud Drive Password": "user",
	# The copies of their data they asked for, with the files.
	"Personal Data Download Request": "user",
}

#: How long after one copy another may be asked for.
AGAIN_AFTER_MINUTES = 60


def settle() -> None:
	roles.grant(GRANTS)


def _administrators() -> list[str]:
	"""The workspace's administrators who are people."""
	from onedesk.one.settings import NOT_PEOPLE

	return [one for one in roles.administrators() if one not in NOT_PEOPLE]


def _mine(user: str | None = None) -> str:
	user = user or frappe.session.user
	from onedesk.one.settings import NOT_PEOPLE

	if user in NOT_PEOPLE:
		frappe.throw(_("This account is not a person's."), frappe.PermissionError)
	return user


def state(user: str | None = None) -> dict:
	"""What the Profile page shows: the last copy asked for, and a deletion
	asked for and not yet done."""
	user = user or frappe.session.user
	copy = frappe.get_all(
		DOWNLOAD, filters={"user": user}, fields=["name", "creation"], order_by="creation desc", limit=1
	)
	file = None
	if copy:
		file = frappe.db.get_value(
			"File",
			{"attached_to_doctype": DOWNLOAD, "attached_to_name": copy[0].name},
			["file_url", "file_size"],
			as_dict=True,
		)
	deletion = frappe.get_all(
		DELETION,
		filters={"email": user, "status": ["in", ["Pending Approval", "On Hold"]]},
		fields=["name", "status", "creation"],
		limit=1,
	)
	held = deletion and deletion[0].status == "On Hold"
	return {
		"copy": {"on": copy[0].creation, "url": file and file.file_url, "ready": bool(file)}
		if copy
		else None,
		"deletion": {
			"status": deletion[0].status,
			"on": deletion[0].creation,
			"why": _held_because(deletion[0].name) if held else None,
		}
		if deletion
		else None,
	}


def _held_because(name: str) -> str | None:
	return frappe.db.get_value(
		"Comment",
		{"reference_doctype": DELETION, "reference_name": name, "comment_type": "Info"},
		"content",
		order_by="creation desc",
	)


# ------------------------------------------------------------------ a copy


@frappe.whitelist(methods=["POST"])
def ask_for_copy() -> dict:
	"""A copy of everything the person left in the workspace, gathered in the
	background and handed to them on their bell and by mail."""
	user = _mine()
	since = add_to_date(now_datetime(), minutes=-AGAIN_AFTER_MINUTES)
	if frappe.db.exists(DOWNLOAD, {"user": user, "creation": [">", since]}):
		frappe.throw(_("You asked for a copy less than an hour ago; it is on its way."))
	# frappe's insert would gather it and mail its own message; One gathers it
	# below and says so through the hub, so the record is written as it is.
	doc = frappe.get_doc({"doctype": DOWNLOAD, "user": user, "user_name": frappe.utils.get_fullname(user)})
	doc.set_new_name()
	doc.set_user_and_timestamp()
	doc.db_insert()
	frappe.enqueue(gather, queue="short", request=doc.name, enqueue_after_commit=True)
	return state(user)


def gather(request: str) -> None:
	"""frappe's own gathering (get_user_data, as its download request does), a
	file only the person may open, and the news on their bell."""
	doc = frappe.get_doc(DOWNLOAD, request)
	data = get_user_data(doc.user)
	file = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"Personal-Data-{doc.user_name.replace(' ', '-')}-{doc.name}.json",
			"attached_to_doctype": DOWNLOAD,
			"attached_to_name": doc.name,
			"content": data,
			"is_private": 1,
		}
	)
	file.flags.skip_file_size_check = True
	file.save(ignore_permissions=True)
	frappe.db.set_value("File", file.name, "owner", doc.user, update_modified=False)
	frappe.db.set_value(DOWNLOAD, doc.name, "owner", doc.user, update_modified=False)
	from onedesk.one import notify

	notify.notify("Your Data Is Ready", doc.user, link="/desk/settings?section=profile", url=file.file_url)
	frappe.publish_realtime("one_privacy", user=doc.user)


# ------------------------------------------------------------------ deletion


def _guard(user: str) -> None:
	"""The last administrator and the person billed for the workspace hand
	those on before they go."""
	if roles.administers(user) and not [one for one in _administrators() if one != user]:
		frappe.throw(_("You are the workspace's only administrator. Make somebody else one first."))
	billed_to = frappe.db.get_single_value("Workspace Account", "billed_to")
	if billed_to and billed_to.lower() == user.lower():
		frappe.throw(
			_("The workspace is billed to this account. Move who pays on Workspace › Plan and Credits first.")
		)


@frappe.whitelist(methods=["POST"])
def ask_to_delete(password: str) -> dict:
	"""The person's own account to be deleted, confirmed with their password,
	and the workspace's administrators asked to approve it."""
	from frappe.utils.password import check_password

	user = _mine()
	try:
		check_password(user, password)
	except frappe.AuthenticationError:
		frappe.throw(_("That is not your password."), title=_("Not deleted"))
	_guard(user)
	if frappe.db.exists(DELETION, {"email": user, "status": ["in", ["Pending Approval", "On Hold"]]}):
		frappe.throw(_("You have asked already; an administrator decides."))
	# Confirmed by the password just typed, so frappe's mailed confirmation
	# link, written for somebody not signed in, is not needed.
	doc = frappe.get_doc({"doctype": DELETION, "email": user, "status": "Pending Approval"})
	doc.set_new_name()
	doc.set_user_and_timestamp()
	doc.db_insert()
	from onedesk.one import notify

	notify.notify(
		"Deletion Asked",
		_administrators(),
		record=(DELETION, doc.name),
		person=frappe.utils.get_fullname(user),
		email=user,
	)
	return state(user)


@frappe.whitelist(methods=["POST"])
def withdraw() -> dict:
	"""The person changed their mind before it was approved."""
	user = _mine()
	for name in frappe.get_all(
		DELETION, filters={"email": user, "status": ["in", ["Pending Approval", "On Hold"]]}, pluck="name"
	):
		frappe.delete_doc(DELETION, name, ignore_permissions=True)
	return state(user)


def _waiting(name: str):
	roles.require()
	doc = frappe.get_doc(DELETION, name)
	approved = not frappe.db.get_value("User", doc.email, "enabled")
	if doc.status not in ("Pending Approval", "On Hold") or approved:
		frappe.throw(_("This request is not waiting for a decision."))
	return doc


def _turn_off(user: str) -> None:
	"""Signed out everywhere and unable to sign in, at once; the erasure
	follows in the background."""
	from frappe.sessions import clear_sessions

	frappe.db.set_value("User", user, "enabled", 0)
	clear_sessions(user=user, force=True)


@frappe.whitelist(methods=["POST"])
def hold(name: str, why: str) -> None:
	"""Kept for now, for a reason the person is told: what the law or an open
	matter makes the workspace keep."""
	doc = _waiting(name)
	why = (why or "").strip()
	if not why:
		frappe.throw(_("Say why, so they know."))
	doc.db_set("status", "On Hold")
	doc.add_comment("Info", why)
	from onedesk.one import notify

	notify.notify("Deletion On Hold", doc.email, link="/desk/settings?section=profile", why=why)


@frappe.whitelist(methods=["POST"])
def approve(name: str) -> None:
	"""Deleted: the person is signed out and turned off now, and erased in
	the background."""
	doc = _waiting(name)
	_guard(doc.email)
	if doc.email == frappe.session.user:
		frappe.throw(_("Another administrator approves deleting your own account."))
	from onedesk.one import notify

	person = frappe.utils.get_fullname(doc.email)
	# Told while there is still somebody to tell.
	notify.notify("Account Deleted", doc.email)
	others = [one for one in _administrators() if one not in (frappe.session.user, doc.email)]
	if others:
		notify.notify("Person Deleted", others, by=frappe.utils.get_fullname(), person=person)
	doc.add_comment("Info", _("Approved by {0}").format(frappe.utils.get_fullname()))
	_turn_off(doc.email)
	frappe.enqueue(erase, queue="long", timeout=3000, request=name, enqueue_after_commit=True)


def erase(request: str) -> None:
	"""What is only theirs deleted, then frappe's own erasure, as frappe runs
	it (with its rights: renaming an account and redacting every log is the
	system's to do, after an administrator approved it above)."""
	frappe.set_user("Administrator")
	doc = frappe.get_doc(DELETION, request)
	for doctype, field in ONLY_THEIRS.items():
		if not frappe.db.exists("DocType", doctype):
			continue
		for name in frappe.get_all(doctype, filters={field: doc.email}, pluck="name"):
			frappe.delete_doc(doctype, name, ignore_permissions=True, force=True, delete_permanently=True)
	frappe.db.commit()
	doc._anonymize_data(commit=True)
	# The request itself is the record that it was done, kept under the
	# anonymous name like everything else.
	frappe.db.set_value(DELETION, request, "email", request, update_modified=False)
	frappe.db.commit()


# ------------------------------------------------------------------ guards


def query(user: str | None = None) -> str | None:
	"""permission_query_conditions: the requests are the administrators'."""
	user = user or frappe.session.user
	if user == "Administrator" or roles.administers(user):
		return None
	return "1=0"


def has_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
	"""Read only, and an administrator's: deciding goes through `hold` and
	`approve`, never by editing the record."""
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	return ptype in ("read", "report", None) and roles.administers(user)


def preview(name: str) -> dict:
	"""What deleting a request's person would do, kind by kind, without doing
	it: what is deleted outright, where their name and address are taken out,
	and what they still hold that somebody should take over."""
	roles.require()
	doc = frappe.get_doc(DELETION, name)
	email = doc.email
	deleted = {
		doctype: frappe.db.count(doctype, {field: email})
		for doctype, field in ONLY_THEIRS.items()
		if frappe.db.exists("DocType", doctype)
	}
	redacted = {}
	for hook in frappe.get_hooks("user_data_fields"):
		doctype, field = hook["doctype"], hook.get("filter_by", "owner")
		if hook.get("strict") or not frappe.db.exists("DocType", doctype):
			continue
		try:
			count = frappe.db.count(doctype, {field: email})
		except Exception:
			continue
		if count:
			redacted[doctype] = redacted.get(doctype, 0) + count
	open_tasks = frappe.db.count("ToDo", {"allocated_to": email, "status": "Open"})
	employee = frappe.db.get_value("Employee", {"user_id": email}, ["name", "status"], as_dict=True)
	return {
		"person": frappe.utils.get_fullname(email),
		"email": email,
		"status": doc.status,
		"deleted_outright": {k: v for k, v in deleted.items() if v},
		"name_and_address_taken_out": redacted,
		"also": "Their name and address are replaced in every comment, change, sign-in, export and the Recycle "
		"Bin; records they made stay, shown as made by a deleted user.",
		"still_assigned_to_them": open_tasks,
		"employee": {"record": employee.name, "status": employee.status} if employee else None,
		"blocked": _blocked(email),
	}


def _blocked(user: str) -> str | None:
	try:
		_guard(user)
	except frappe.ValidationError as e:
		return str(e)
	return None
