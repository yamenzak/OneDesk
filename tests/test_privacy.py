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
HOOKS = (tree.APP / "hooks.py").read_text()


def _body(name: str, source: str = SOURCE) -> str:
	return source.split(f"def {name}(", 1)[1].split("\ndef ", 1)[0]


def test_the_request_is_guarded_and_decided_only_through_one():
	assert '"Personal Data Deletion Request": "onedesk.one.privacy.has_permission"' in HOOKS
	assert '"Personal Data Deletion Request": "onedesk.one.privacy.query"' in HOOKS
	assert 'ptype in ("read", "report", None) and roles.administers(user)' in _body("has_permission")
	assert 'return "1=0"' in _body("query")
	assert "roles.require()" in _body("_waiting")
	assert "write" not in SOURCE.split("GRANTS = ", 1)[1].split("\n", 1)[0]


def test_only_the_person_asks_and_proves_it_is_them():
	asked = _body("ask_to_delete")
	assert "check_password(user, password" in asked and "_mine()" in asked
	assert "mailed = not _has_password(user)" in asked and "_mail_confirmation(doc)" in asked
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


def test_nobody_removes_the_last_administrator_or_the_payer_or_themselves():
	guard = _body("_guard")
	assert "_administrators()" in guard and '"billed_to"' in guard
	approve = _body("approve")
	assert "_guard(doc.email)" in approve and "doc.email == frappe.session.user" in approve
	assert "_guard(user)" in _body("ask_to_delete")


def test_approving_signs_them_out_then_erases_as_frappe_does():
	approve = _body("approve")
	assert "_turn_off(doc.email)" in approve and "frappe.enqueue(erase" in approve
	assert "clear_sessions(user=user, force=True)" in _body("_turn_off")
	erase = _body("erase")
	assert "ONLY_THEIRS.items()" in erase and "doc._anonymize_data(commit=True)" in erase
	assert 'frappe.db.set_value(DELETION, request, "email", request' in erase
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
	assert "set(withheld) - optional" in send and "withheld and not why" in send
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
	assert 'notify.notify(\n\t\t"Your Data Is Ready"' in gather or '"Your Data Is Ready"' in gather
	assert 'ptype in ("read", "report", None) and roles.administers(user)' in _body("has_permission", COPY)
	assert '"attached_to_doctype": "User"' in _body("_file_of", COPY) and '"attached_to_name": user' in _body(
		"_file_of", COPY
	)
	assert '"file_name": ["like", "Personal-Data-%"]' in _body("erase")
	assert '"role": "All"' in _body("settle")


def test_everybody_concerned_is_told():
	types = (tree.APP / "one" / "notifications.py").read_text()
	for name in (
		"Your Data Is Ready",
		"Deletion Asked",
		"Deletion On Hold",
		"Account Deleted",
		"Person Deleted",
	):
		assert f'_lt("{name}")' in types, name
	assert '"Deletion Asked"' in _body("_ask_administrators")
	assert '"Copy Asked"' in _body("ask", COPY)
	assert '"onedesk.one.privacy.remind"' in HOOKS
	assert '"Deletion On Hold"' in _body("hold")


def test_the_sidebar_and_the_profile_reach_it():
	sidebar = json.loads((tree.APP / "one" / "sidebar" / "one" / "one.json").read_text())
	links = {one["link_to"]: one["label"] for one in sidebar["items"] if one.get("link_type") == "DocType"}
	assert links["Personal Data Deletion Request"] == "Account Deletions"
	assert links["Personal Data Download Request"] == "Data Copies"
	page = (tree.APP / "public" / "js" / "settings.js").read_text()
	for method in ("privacy_copy.ask", "privacy.ask_to_delete", "privacy.withdraw"):
		assert f"onedesk.one.{method}" in page, method


PUBLIC = (tree.APP / "one" / "privacy_public.py").read_text()


def test_somebody_who_is_not_a_user_asks_on_the_page_by_a_mailed_link():
	assert '{"from_route": "/your-data", "to_route": "your_data"}' in HOOKS
	ask = _body("ask", PUBLIC)
	assert "@rate_limit(limit=ASKS_AN_HOUR" in PUBLIC.split("def ask(", 1)[0].rsplit("\n\n\n", 1)[1]
	assert 'notify.mail(\n\t\t"Confirm Your Request"' in ask
	assert 'return {"said": ' in ask and "exists(" not in ask, (
		"the page answers the same whatever the address"
	)
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
	assert '"Your Data Is Ready to Download"' in _body("gather", COPY)


def test_deleting_them_redacts_as_frappe_does_with_no_account_to_rename():
	erase = _body("erase", PUBLIC)
	assert "redact_full_match_data" in erase and "redact_partial_match_data" in erase
	assert "_anonymize_data(" not in erase and "rename_doc" not in erase
	assert '"status": "Deleted", "email": anon' in erase
	assert "privacy_public.erase(doc)" in _body("erase")
	approve = _body("approve")
	assert '"Your Data Is Being Deleted"' in approve and "_is_user(doc.email)" in approve


def test_somebody_who_is_not_a_user_can_find_the_page():
	brand = (tree.APP / "one" / "brand.py").read_text()
	assert '{"label": "Your Data", "url": "/your-data"}' in brand
	assert '"footer_powered": " "' in brand, "an empty one draws erpnext's line"
	login = (tree.APP / "public" / "js" / "login.js").read_text()
	assert '["/your-data", __("Your Data")]' in login and "frappe._translations_loaded" in login
	assert "onedesk.one.patches.your_data_footer" in (tree.APP / "patches.txt").read_text()
