"""Privacy requests (one/privacy.py): anybody gets a copy of their own data or
asks for their account to be deleted, an administrator decides a deletion,
and approving runs frappe's own erasure after deleting what is only the
person's. These read the code that says so."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

SOURCE = (tree.APP / "one" / "privacy.py").read_text()
COPY = (tree.APP / "one" / "privacy_copy.py").read_text()
TELL = (tree.APP / "one" / "tell.py").read_text()
HOOKS = (tree.APP / "hooks.py").read_text()


def _body(name: str, source: str = SOURCE) -> str:
	return source.split(f"def {name}(", 1)[1].split("\ndef ", 1)[0]


def test_the_request_is_guarded_and_decided_only_through_one():
	assert '"Personal Data Deletion Request": "onedesk.one.privacy.has_permission"' in HOOKS
	assert '"Personal Data Deletion Request": "onedesk.one.privacy.query"' in HOOKS
	assert "roles.require()" in _body("_waiting")
	granted = tree.granted()
	for doctype in ("Personal Data Deletion Request", "Personal Data Download Request"):
		assert "write" not in granted[doctype], doctype


def test_only_the_person_asks_and_proves_it_is_them():
	assert "_mine()" in _body("ask", COPY) and "_mine()" in _body("withdraw")


def test_a_mailed_link_is_signed_and_lasts_a_day():
	assert "get_signed_params(" in _body("_mail_confirmation")
	confirm = _body("confirm")
	assert "verify_request()" in confirm
	assert (
		'doc.status != "Pending Verification"' in confirm
		and "get_datetime(expires) < now_datetime()" in confirm
	)
	assert "LINK_HOURS = 24" in SOURCE


def test_approving_signs_them_out_then_erases_as_frappe_does():
	for doctype in ("AI Chat", "AI Memory", "Notification Log", "Push Device"):
		assert f'"{doctype}"' in SOURCE.split("ONLY_THEIRS = {", 1)[1].split("}", 1)[0], doctype


def test_the_bin_and_the_logs_lose_the_name_too():
	fields = HOOKS.split("user_data_fields = [", 1)[1].split("\n]", 1)[0]
	assert '{"doctype": doctype, "strict": True}' in fields
	for doctype in ("Deleted Document", "ToDo", "Notification Log"):
		assert f'"{doctype}"' in fields, doctype


def test_what_is_about_them_always_goes_and_the_rest_is_reviewed():
	kinds = COPY.split("KINDS = (", 1)[1].split("\n)", 1)[0]
	for key in ("account", "signins", "contacts", "memory", "agreements"):
		line = kinds.split(f'("{key}", ', 1)[1].split("\n", 1)[0]
		assert line.endswith("True),"), key
	send = _body("send", COPY)
	assert "roles.require()" in send
	assert '"one_withheld": said' in send


def test_the_copy_never_carries_the_workspaces_values():
	gather = _body("gather_kind", COPY)
	assert "reset_password_key" not in COPY and "api_key" not in COPY
	assert '"page"' not in gather and "Deleted Document" not in gather
	assert 'one["fields"] = [label(change[0])' in gather
	assert "import get_user_data" not in COPY and "get_user_data(" not in COPY


def test_the_copy_is_the_persons_alone():
	gather = _body("gather", COPY)
	assert '"is_private": 1' in gather and '"owner", doc.user' in gather
	assert '"role": "All"' in _body("_no_copies_in_the_sidebar", (tree.APP / "one" / "access.py").read_text())


def test_everybody_concerned_is_told():
	types = tree.notifications()
	for name in (
		"Your Data Is Ready",
		"Deletion Asked",
		"Deletion On Hold",
		"Account Deleted",
		"Person Deleted",
	):
		assert name in types, name
	assert "tell.deletion_asked(doc)" in _body("confirm"), "asked by the mailed link too"
	assert '"onedesk.one.privacy.remind"' in HOOKS


def test_the_sidebar_and_the_profile_reach_it():
	sidebar = json.loads((tree.APP / "one" / "sidebar" / "one" / "one.json").read_text())
	links = {one["link_to"]: one["label"] for one in sidebar["items"] if one.get("link_type") == "DocType"}
	assert links["Personal Data Deletion Request"] == "Account Deletions"
	assert links["Personal Data Download Request"] == "Data Copies"
	page = (tree.APP / "public" / "js" / "one_account" / "account_center.js").read_text()
	for method in ("privacy_copy.ask", "privacy.ask_to_delete", "privacy.withdraw"):
		assert f"onedesk.one.{method}" in page, method


PUBLIC = (tree.APP / "one" / "privacy_public.py").read_text()


def test_somebody_who_is_not_a_user_asks_on_the_page_by_a_mailed_link():
	assert '{"from_route": "/your-data", "to_route": "your_data"}' in HOOKS
	ask = _body("ask", PUBLIC)
	assert "@rate_limit(limit=ASKS_AN_HOUR" in PUBLIC.split("def ask(", 1)[0].rsplit("\n\n\n", 1)[1]
	assert "tell.request_to_confirm(" in ask
	assert 'notify.mail(\n\t\t"Confirm Your Request"' in _body("request_to_confirm", TELL)
	confirm = _body("confirm", PUBLIC)
	assert "verify_request()" in confirm and "get_datetime(expires) < now_datetime()" in confirm
	assert 'frappe.set_user("Guest")' in confirm.split("finally:", 1)[1]
	assert "LINK_HOURS = 24" in PUBLIC


def test_their_copy_is_what_is_about_them_and_reached_only_by_its_link():
	assert 'OUTSIDER = ("contacts", "records", "mail")' in COPY
	kinds = COPY.split("KINDS = (", 1)[1].split("\n)", 1)[0]
	assert kinds.split('("records", ', 1)[1].split("\n", 1)[0].endswith("True),")
	download = _body("download", PUBLIC)
	assert "verify_request()" in download and "get_datetime(expires) < now_datetime()" in download
	assert "DOWNLOAD_DAYS = 7" in PUBLIC
	assert "tell.copy_ready_to_download(doc.name, address, withheld_said)" in _body("gather", COPY)
	assert '"Your Data Is Ready to Download"' in _body("copy_ready_to_download", TELL)


def test_deleting_them_redacts_as_frappe_does_with_no_account_to_rename():
	erase = _body("erase", PUBLIC)
	assert "_anonymize_data(" not in erase and "rename_doc" not in erase
	approve = _body("approve")
	assert "tell.deletion_approved(doc, user)" in approve
	assert '"Your Data Is Being Deleted"' in _body("deletion_approved", TELL)


def test_somebody_who_is_not_a_user_can_find_the_page():
	brand = (tree.APP / "one" / "brand.py").read_text()
	assert '{"label": "Your Data", "url": "/your-data"}' in brand
	assert '"footer_powered": " "' in brand, "an empty one draws erpnext's line"
	login = (tree.APP / "public" / "js" / "login.js").read_text()
	assert '["/your-data", __("Your Data")]' in login and "frappe._translations_loaded" in login
	assert "onedesk.one.patches.your_data_footer" in (tree.APP / "patches.txt").read_text()


def test_the_public_page_is_frappes_sign_in_card():
	page = (tree.APP / "www" / "your_data.html").read_text()
	guest = page
	assert 'include_style("login.bundle.css")' in page and "import alert_banner" in page
	assert '<section class="for-login one-your-data">' in guest and 'class="login-content page-card' in guest
	assert 'alert_banner("success")' in guest and 'alert_banner("error")' in guest
	assert "new frappe.ui.TabButtons(" in guest and 'class="es-button w-full" data-variant="solid"' in guest
	for hand_drawn in ("one-go", "one-choice", "one-field", "<fieldset"):
		assert hand_drawn not in guest, hand_drawn
	login = (tree.APP / "public" / "js" / "login.js").read_text()
	assert login.count(".for-login:not(.one-your-data)") == 2, "the passkey and the footnote stay on sign-in"
	context = (tree.APP / "www" / "your_data.py").read_text()
	assert "raise frappe.Redirect" in context and "privacy.where(frappe.session.user)" in context


def test_a_mailed_link_that_no_longer_works_offers_to_ask_again():
	page = _body("_page", PUBLIC)
	assert 'primary_action="/" if ok else "/your-data"' in page and '_("Ask Again")' in page
