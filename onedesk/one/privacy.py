"""Privacy Requests: a copy of your data, and your account deleted.
docs/DESK-COVERAGE.md, P2.

Frappe has both: a `Personal Data Download Request` that gathers what a person
left across the workspace (the `user_data_fields` hooks) into one file, and a
`Personal Data Deletion Request` that redacts their name and address from
those records, disables the account and renames it to an anonymous one. Both
are driven by its System Manager and its own mails ("Dear User"), and nobody
on a workspace is either. Here:

- anybody asks from You > Profile: a copy of their data, which an
  administrator reviews first (one/privacy_copy.py); or their account
  deleted, confirmed with their password, or by a link One mails them when
  they sign in without one, because it cannot be undone;
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
from frappe.utils import add_days, add_to_date, get_datetime, now_datetime
from frappe.utils.verified_command import get_signed_params, verify_request

from onedesk.one import roles

DOWNLOAD = "Personal Data Download Request"
DELETION = "Personal Data Deletion Request"

GRANTS = {DELETION: ("read", "report"), DOWNLOAD: ("read", "report")}

#: What is only the person's and of no use to the workspace once they are
#: gone: deleted outright before frappe's erasure, as {doctype: field}.
ONLY_THEIRS = {
	"AI Chat": "owner",
	"AI Memory": "owner",
	"Notification Log": "for_user",
	"Push Device": "user",
	"Calendar Feed": "user",
	"Cloud Drive Password": "user",
	# The copies of their data they asked for (the files go too, below).
	"Personal Data Download Request": "user",
}

#: How long a mailed confirmation link works.
LINK_HOURS = 24

#: After how many days a request nobody decided reminds the administrators.
REMIND_AFTER_DAYS = 7

#: Where a deletion waits: confirmed, or for the person's mailed link.
OPEN = ("Pending Verification", "Pending Approval", "On Hold")


def settle() -> None:
	"""The administrator's read on both kinds of request. Frappe also lets
	everybody read their own copy requests, which put Data Copies in every
	person's sidebar; the person sees theirs on their profile instead."""
	from frappe.permissions import setup_custom_perms

	roles.grant(GRANTS)
	setup_custom_perms(DOWNLOAD)
	for name in frappe.get_all("Custom DocPerm", filters={"parent": DOWNLOAD, "role": "All"}, pluck="name"):
		frappe.delete_doc("Custom DocPerm", name, ignore_permissions=True)
		frappe.clear_cache(doctype=DOWNLOAD)


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
	"""What the Profile page shows: the last copy asked for, a deletion asked
	for and not yet done, and whether deleting is confirmed with a password."""
	from onedesk.one import privacy_copy

	user = user or frappe.session.user
	deletion = frappe.get_all(
		DELETION,
		filters={"email": user, "status": ["in", list(OPEN)]},
		fields=["name", "status", "creation"],
		limit=1,
	)
	held = deletion and deletion[0].status == "On Hold"
	return {
		"copy": privacy_copy.last(user),
		"deletion": {
			"status": deletion[0].status,
			"on": deletion[0].creation,
			"why": _held_because(deletion[0].name) if held else None,
		}
		if deletion
		else None,
		"password": _has_password(user),
	}


def _has_password(user: str) -> bool:
	"""Whether the person signs in with a password at all: somebody who signs
	in by mailed link or passkey confirms by mail instead."""
	return bool(
		frappe.db.sql(
			"select 1 from `__Auth` where doctype='User' and name=%s and fieldname='password' limit 1", user
		)
	)


def _held_because(name: str) -> str | None:
	return frappe.db.get_value(
		"Comment",
		{"reference_doctype": DELETION, "reference_name": name, "comment_type": "Info"},
		"content",
		order_by="creation desc",
	)


# ------------------------------------------------------------------ deletion


def _guard(user: str) -> None:
	"""The last administrator and the person billed for the workspace hand
	those on before they go."""
	if roles.administers(user) and not [one for one in _administrators() if one != user]:
		frappe.throw(_("You're the only administrator. Make someone else an administrator first."))
	billed_to = frappe.db.get_single_value("Workspace Account", "billed_to")
	if billed_to and billed_to.lower() == user.lower():
		frappe.throw(
			_("The workspace is billed to this account. Change who pays in Workspace › Plan and Credits first.")
		)


@frappe.whitelist(methods=["POST"])
def ask_to_delete(password: str | None = None) -> dict:
	"""The person's own account to be deleted. Confirmed with their password,
	or, when they sign in without one, by a link One mails them; then the
	workspace's administrators are asked to approve it."""
	from frappe.utils.password import check_password

	user = _mine()
	_guard(user)
	if frappe.db.exists(DELETION, {"email": user, "status": ["in", list(OPEN)]}):
		frappe.throw(_("You've already asked. An administrator will decide."))
	mailed = not _has_password(user)
	if not mailed:
		try:
			check_password(user, password or "")
		except frappe.AuthenticationError:
			frappe.throw(_("That is not your password."), title=_("Not deleted"))
	# frappe's insert mails its own confirmation, written for somebody not
	# signed in; One confirms with the password just typed, or its own mail.
	doc = frappe.get_doc(
		{
			"doctype": DELETION,
			"email": user,
			"status": "Pending Verification" if mailed else "Pending Approval",
		}
	)
	doc.set_new_name()
	doc.set_user_and_timestamp()
	doc.db_insert()
	if mailed:
		_mail_confirmation(doc)
	else:
		_ask_administrators(doc)
	return state(user)


def _mail_confirmation(doc) -> None:
	from onedesk.one import notify

	expires = add_to_date(now_datetime(), hours=LINK_HOURS).strftime("%Y-%m-%d %H:%M:%S")
	url = (
		frappe.utils.get_url("/api/method/onedesk.one.privacy.confirm")
		+ "?"
		+ get_signed_params({"name": doc.name, "expires": expires})
	)
	notify.notify("Confirm Deletion", doc.email, url=url, hours=LINK_HOURS)


def _ask_administrators(doc) -> None:
	from onedesk.one import notify

	notify.notify(
		"Deletion Asked",
		_administrators(),
		record=(DELETION, doc.name),
		person=frappe.utils.get_fullname(doc.email),
		email=doc.email,
	)


@frappe.whitelist(allow_guest=True, methods=["GET"])
def confirm(name: str, expires: str) -> None:
	"""The link One mailed: the request goes to the administrators. Signed,
	so it cannot be made up, and good for a day."""
	if not verify_request():
		return
	doc = frappe.get_doc(DELETION, name) if frappe.db.exists(DELETION, name) else None
	if not doc or doc.status != "Pending Verification" or get_datetime(expires) < now_datetime():
		frappe.respond_as_web_page(
			_("This link no longer works"),
			_("Ask again from your profile if you still want your account deleted."),
			indicator_color="red",
		)
		return
	doc.db_set("status", "Pending Approval")
	_ask_administrators(doc)
	frappe.db.commit()
	frappe.respond_as_web_page(
		_("Confirmed"),
		_("Your request is with your workspace's administrators. You will hear when they decide."),
		indicator_color="green",
	)


@frappe.whitelist(methods=["POST"])
def withdraw() -> dict:
	"""The person changed their mind before it was approved."""
	user = _mine()
	for name in frappe.get_all(DELETION, filters={"email": user, "status": ["in", list(OPEN)]}, pluck="name"):
		frappe.delete_doc(DELETION, name, ignore_permissions=True)
	return state(user)


def _waiting(name: str):
	roles.require()
	doc = frappe.get_doc(DELETION, name)
	# An account turned off has been approved already; somebody who is not a
	# user has no account to turn off.
	approved = frappe.db.exists("User", doc.email) and not frappe.db.get_value("User", doc.email, "enabled")
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

	if _is_user(doc.email):
		notify.notify("Deletion On Hold", doc.email, link="/desk/settings?section=profile", why=why)
	else:
		notify.mail("Your Request Is On Hold", doc.email, why=why)


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
	user = _is_user(doc.email)
	# Told while there is still somebody to tell.
	if user:
		notify.notify("Account Deleted", doc.email)
	else:
		notify.mail("Your Data Is Being Deleted", doc.email)
	others = [one for one in _administrators() if one not in (frappe.session.user, doc.email)]
	if others:
		notify.notify("Person Deleted", others, by=frappe.utils.get_fullname(), person=person)
	doc.add_comment("Info", _("Approved by {0}").format(frappe.utils.get_fullname()))
	if user:
		_turn_off(doc.email)
	frappe.enqueue(erase, queue="long", timeout=3000, request=name, enqueue_after_commit=True)


def _is_user(email: str) -> bool:
	return bool(frappe.db.exists("User", email))


def erase(request: str) -> None:
	"""What is only theirs deleted, then frappe's own erasure, as frappe runs
	it (with its rights: renaming an account and redacting every log is the
	system's to do, after an administrator approved it above)."""
	frappe.set_user("Administrator")
	doc = frappe.get_doc(DELETION, request)
	if not _is_user(doc.email):
		from onedesk.one import privacy_public

		return privacy_public.erase(doc)
	for doctype, field in ONLY_THEIRS.items():
		if not frappe.db.exists("DocType", doctype):
			continue
		for name in frappe.get_all(doctype, filters={field: doc.email}, pluck="name"):
			frappe.delete_doc(doctype, name, ignore_permissions=True, force=True, delete_permanently=True)
	# The copies of their data, kept on their account.
	for name in frappe.get_all(
		"File",
		filters={
			"attached_to_doctype": "User",
			"attached_to_name": doc.email,
			"file_name": ["like", "Personal-Data-%"],
		},
		pluck="name",
	):
		frappe.delete_doc("File", name, ignore_permissions=True, force=True, delete_permanently=True)
	frappe.db.commit()
	doc._anonymize_data(commit=True)
	# The request itself is the record that it was done, kept under the
	# anonymous name like everything else.
	frappe.db.set_value(DELETION, request, "email", request, update_modified=False)
	frappe.db.commit()


def remind() -> None:
	"""scheduler_events daily: requests nobody has decided after a week, said
	again to the administrators. The law gives a month to answer."""
	from onedesk.one import notify

	since = add_days(now_datetime(), -REMIND_AFTER_DAYS)
	waiting = frappe.db.count(DELETION, {"status": "Pending Approval", "creation": ["<", since]})
	waiting += frappe.db.count(DOWNLOAD, {"one_status": "Waiting", "creation": ["<", since]})
	if waiting:
		notify.notify(
			"Privacy Requests Waiting",
			_administrators(),
			link="/desk/personal-data-download-request",
			count=waiting,
		)


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
