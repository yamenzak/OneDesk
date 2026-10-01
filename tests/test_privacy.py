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
HOOKS = (tree.APP / "hooks.py").read_text()


def _body(name: str) -> str:
	return SOURCE.split(f"def {name}(", 1)[1].split("\ndef ", 1)[0]


def test_the_request_is_guarded_and_decided_only_through_one():
	assert '"Personal Data Deletion Request": "onedesk.one.privacy.has_permission"' in HOOKS
	assert '"Personal Data Deletion Request": "onedesk.one.privacy.query"' in HOOKS
	assert 'ptype in ("read", "report", None) and roles.administers(user)' in _body("has_permission")
	assert 'return "1=0"' in _body("query")
	assert "roles.require()" in _body("_waiting")
	assert "write" not in SOURCE.split("GRANTS = ", 1)[1].split("\n", 1)[0]


def test_only_the_person_asks_and_with_their_password():
	asked = _body("ask_to_delete")
	assert "check_password(user, password)" in asked and "_mine()" in asked
	assert "_mine()" in _body("ask_for_copy") and "_mine()" in _body("withdraw")
	assert "AGAIN_AFTER_MINUTES" in _body("ask_for_copy")


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


def test_the_copy_is_frappes_gathering_and_only_theirs():
	gather = _body("gather")
	assert "get_user_data(doc.user)" in gather and '"is_private": 1' in gather
	assert 'notify.notify("Your Data Is Ready", doc.user' in gather


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
	assert '"Deletion Asked"' in _body("ask_to_delete")
	assert '"Deletion On Hold"' in _body("hold")


def test_the_sidebar_and_the_profile_reach_it():
	sidebar = json.loads((tree.APP / "one" / "sidebar" / "one" / "one.json").read_text())
	links = {one["link_to"]: one["label"] for one in sidebar["items"] if one.get("link_type") == "DocType"}
	assert links["Personal Data Deletion Request"] == "Privacy Requests"
	page = (tree.APP / "public" / "js" / "settings.js").read_text()
	for method in ("ask_for_copy", "ask_to_delete", "withdraw"):
		assert f"onedesk.one.privacy.{method}" in page, method
