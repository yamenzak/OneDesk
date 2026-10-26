"""Privacy Requests: a copy of your data, and your account deleted.

Frappe's own Personal Data Download and Deletion Requests, asked for by anybody
from their profile and decided by a workspace administrator.
"""

import frappe
from frappe import _
from frappe.utils import add_days, add_to_date, get_datetime, now_datetime
from frappe.utils.verified_command import get_signed_params, verify_request

from onedesk.one import roles, tell

DOWNLOAD = "Personal Data Download Request"
DELETION = "Personal Data Deletion Request"

ONLY_THEIRS = {
	"AI Chat": "owner",
	"AI Memory": "owner",
	"Notification Log": "for_user",
	"Push Device": "user",
	"Calendar Feed": "user",
	"Cloud Drive Password": "user",
	"Personal Data Download Request": "user",
}

LINK_HOURS = 24

REMIND_AFTER_DAYS = 7

OPEN = ("Pending Verification", "Pending Approval", "On Hold")


def _administrators() -> list[str]:
	"""The workspace's administrators who are people."""
	from onedesk.one.people import NOT_PEOPLE

	return [one for one in roles.administrators() if one not in NOT_PEOPLE]


def where(user: str) -> str:
	"""Where somebody reads their requests: their desk profile, Your Data on
	the portal for a customer's or supplier's contact, or the page anybody
	may ask from."""
	if frappe.db.get_value("User", user, "user_type") == "System User":
		return "/desk/one?center=account&at=profile"
	if set(frappe.get_roles(user)) & {"Customer", "Supplier"}:
		return "/portal/your-data"
	return "/your-data"


def _mine(user: str | None = None) -> str:
	user = user or frappe.session.user
	from onedesk.one.people import NOT_PEOPLE

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


def _guard(user: str) -> None:
	"""The last administrator and the person billed for the workspace hand
	those on before they go."""
	if roles.administers(user) and not [one for one in _administrators() if one != user]:
		frappe.throw(_("You're the only administrator. Make someone else an administrator first."))
	billed_to = frappe.db.get_single_value("Workspace Account", "billed_to")
	if billed_to and billed_to.lower() == user.lower():
		frappe.throw(
			_("The workspace is billed to this account. Change who pays in Plan and Credits in AccountCenter first.")
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
		tell.deletion_asked(doc)
	return state(user)


def _mail_confirmation(doc) -> None:
	expires = add_to_date(now_datetime(), hours=LINK_HOURS).strftime("%Y-%m-%d %H:%M:%S")
	url = (
		frappe.utils.get_url("/api/method/onedesk.one.privacy.confirm")
		+ "?"
		+ get_signed_params({"name": doc.name, "expires": expires})
	)
	tell.asked_to_confirm_deletion(doc.email, url, LINK_HOURS)


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
			_("Ask again under Your Data if you still want your account deleted."),
			indicator_color="red",
		)
		return
	doc.db_set("status", "Pending Approval")
	tell.deletion_asked(doc)
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
	tell.deletion_held(doc, why)


@frappe.whitelist(methods=["POST"])
def approve(name: str) -> None:
	"""Deleted: the person is signed out and turned off now, and erased in
	the background."""
	doc = _waiting(name)
	_guard(doc.email)
	if doc.email == frappe.session.user:
		frappe.throw(_("Another administrator approves deleting your own account."))
	user = _is_user(doc.email)
	tell.deletion_approved(doc, user)
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
	frappe.db.set_value(DELETION, request, "email", request, update_modified=False)
	frappe.db.commit()


def remind() -> None:
	"""scheduler_events daily: requests nobody has decided after a week, said
	again to the administrators. The law gives a month to answer."""
	since = add_days(now_datetime(), -REMIND_AFTER_DAYS)
	waiting = frappe.db.count(DELETION, {"status": "Pending Approval", "creation": ["<", since]})
	waiting += frappe.db.count(DOWNLOAD, {"one_status": "Waiting", "creation": ["<", since]})
	if waiting:
		tell.privacy_requests_waiting(waiting)


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


@frappe.whitelist()
@frappe.read_only()
def requests() -> dict:
	"""The workspace's privacy requests, newest first, for TrustCenter's
	Requests: who asked to have their account deleted and who asked for a
	copy of their data. Workspace administrators only."""
	roles.require()
	return {
		"deletions": frappe.get_list(
			"Personal Data Deletion Request", fields=["name", "email", "status", "creation"], order_by="creation desc", limit_page_length=100
		),
		"copies": frappe.get_list(
			"Personal Data Download Request", fields=["name", "user", "user_name", "one_status", "creation"], order_by="creation desc", limit_page_length=100
		),
	}
