"""Your Data, for somebody who is not a user: a customer's contact, a
supplier, a lead, a job applicant. See one/privacy.py and one/privacy_copy.py.

They have the same rights as a user and no account to ask from, so each
workspace's own site has a page, `/your-data` (www/your_data.py): they give
their address and whether they want a copy of what the workspace holds about
them or that deleted. One mails a signed link to that address, so only
whoever reads its mail can ask, and nothing is written until it is opened;
the page says the same whatever the address, so it cannot be used to learn
who the workspace knows.

Opening the link files the request where a user's goes: Workspace > Data
Copies or Account Deletions, for an administrator to review and decide the
same way. A copy for them holds what is about them (contacts and records
with their address) and the mail, which may be withheld; it is mailed as a
link that works for a week. Deleting takes their name and address out of
everything the workspace keeps, by frappe's own redaction, without the step
that renames an account they do not have.

Somebody whose address is a user's gets the same link; opening it files the
request as if they had asked from their profile.
"""

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import add_to_date, get_datetime, now_datetime, validate_email_address
from frappe.utils.verified_command import get_signed_params, verify_request

from onedesk.one import notify

DOWNLOAD = "Personal Data Download Request"
DELETION = "Personal Data Deletion Request"

#: How long a confirmation link works.
LINK_HOURS = 24

#: How long the link to a copy works.
DOWNLOAD_DAYS = 7

#: How many requests one network address may make in an hour.
ASKS_AN_HOUR = 5

KINDS = ("copy", "delete")


def _signed(method: str, **params) -> str:
	return (
		frappe.utils.get_url(f"/api/method/onedesk.one.privacy_public.{method}")
		+ "?"
		+ get_signed_params(params)
	)


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=ASKS_AN_HOUR, seconds=60 * 60)
def ask(email: str, kind: str) -> dict:
	"""Mail a link to confirm a request. Says the same whatever the address."""
	email = (email or "").strip().lower()
	if kind not in KINDS or not validate_email_address(email):
		frappe.throw(_("Give the address the workspace knows you by."))
	expires = add_to_date(now_datetime(), hours=LINK_HOURS).strftime("%Y-%m-%d %H:%M:%S")
	notify.mail(
		"Confirm Your Request",
		email,
		now=False,
		workspace=_workspace(),
		asked=_("a copy of the data it holds about you")
		if kind == "copy"
		else _("the data it holds about you deleted"),
		hours=LINK_HOURS,
		url=_signed("confirm", email=email, kind=kind, expires=expires),
	)
	return {"said": _("If the workspace knows that address, a link to confirm is on its way to it.")}


def _workspace() -> str:
	return frappe.db.get_single_value("Workspace Account", "workspace_name") or frappe.local.site


def _page(title: str, text: str, ok: bool = True) -> None:
	frappe.respond_as_web_page(title, text, indicator_color="green" if ok else "red")


@frappe.whitelist(allow_guest=True, methods=["GET"])
def confirm(email: str, kind: str, expires: str) -> None:
	"""The mailed link, opened: the request goes to the administrators."""
	if not verify_request():
		return
	if get_datetime(expires) < now_datetime() or kind not in KINDS:
		return _page(
			_("This link no longer works"), _("Ask again on the workspace's Your Data page."), ok=False
		)
	frappe.set_user("Administrator")
	try:
		if kind == "copy":
			_ask_copy(email)
		else:
			_ask_deletion(email)
	finally:
		frappe.set_user("Guest")
	frappe.db.commit()
	_page(
		_("Confirmed"),
		_("Your request is with {0}. They decide within a month, and you will hear by mail.").format(
			_workspace()
		),
	)


def _ask_copy(email: str) -> None:
	from onedesk.one import privacy

	user = email if frappe.db.exists("User", email) else None
	if frappe.db.exists(DOWNLOAD, {"one_email": email, "one_status": ["in", ["Waiting", "Gathering"]]}):
		return
	doc = frappe.get_doc(
		{
			"doctype": DOWNLOAD,
			"user": user,
			"user_name": frappe.utils.get_fullname(user) if user else email,
			"one_email": email,
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
		person=frappe.utils.get_fullname(user) if user else email,
	)


def _ask_deletion(email: str) -> None:
	from onedesk.one import privacy

	if frappe.db.exists(DELETION, {"email": email, "status": ["in", list(privacy.OPEN)]}):
		return
	if frappe.db.exists("User", email):
		try:
			privacy._guard(email)
		except frappe.ValidationError:
			# Said to the administrators, who see the request and why it waits.
			pass
	doc = frappe.get_doc({"doctype": DELETION, "email": email, "status": "Pending Approval"})
	doc.set_new_name()
	doc.set_user_and_timestamp()
	doc.db_insert()
	privacy._ask_administrators(doc)


def download_link(request: str) -> str:
	expires = add_to_date(now_datetime(), days=DOWNLOAD_DAYS).strftime("%Y-%m-%d %H:%M:%S")
	return _signed("download", request=request, expires=expires)


@frappe.whitelist(allow_guest=True, methods=["GET"])
def download(request: str, expires: str) -> None:
	"""The copy for somebody who is not a user, through the link mailed to
	them: signed, so it cannot be guessed, and good for a week."""
	if not verify_request():
		return
	if get_datetime(expires) < now_datetime():
		return _page(
			_("This link no longer works"), _("Ask again on the workspace's Your Data page."), ok=False
		)
	from onedesk.one import privacy_copy

	name = frappe.db.get_value("File", privacy_copy._outsider_file(request), "name")
	if not name:
		return _page(_("This copy is gone"), _("Ask again on the workspace's Your Data page."), ok=False)
	file = frappe.get_doc("File", name)
	frappe.local.response.filename = file.file_name
	frappe.local.response.filecontent = file.get_content()
	frappe.local.response.type = "download"


def erase(doc) -> None:
	"""Frappe's redaction for somebody who is not a user, as its own
	`_anonymize_data` runs it, without the last step, which renames an
	account they do not have. Run as Administrator by privacy.erase."""
	email, anon = doc.email, doc.name
	# frappe's own, name-mangled: the patterns for the address and the name.
	doc._PersonalDataDeletionRequest__set_anonymization_data(email, anon)
	doc.add_deletion_steps()
	for ref in doc.full_match_privacy_docs:
		doc.redact_full_match_data(ref, email)
		doc.set_step_status(ref["doctype"])
	for ref in doc.partial_privacy_docs:
		doc.redact_partial_match_data(ref)
		doc.set_step_status(ref["doctype"])
	# The copies of their data, with their files.
	for name in frappe.get_all(DOWNLOAD, filters={"one_email": email}, pluck="name"):
		frappe.delete_doc(DOWNLOAD, name, ignore_permissions=True, force=True, delete_permanently=True)
	frappe.db.set_value(DELETION, doc.name, {"status": "Deleted", "email": anon}, update_modified=False)
	frappe.db.commit()
