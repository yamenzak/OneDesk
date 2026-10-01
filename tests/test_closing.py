"""Closing a workspace (one/closing.py, one_admin/closing.py): only its payer
takes everything or closes it, closing waits out a notice and then walks the
ladder's own Archive, and nothing without a closing day is ever touched.
These read the code that says so."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

HERE = (tree.APP / "one" / "closing.py").read_text()
THERE = (tree.APP / "one_admin" / "closing.py").read_text()
PROXY = (tree.APP / "one_admin" / "proxy.py").read_text()
TELL = (tree.APP / "one_admin" / "tell.py").read_text()
HOOKS = (tree.APP / "hooks.py").read_text()


def _body(name: str, source: str) -> str:
	return source.split(f"def {name}(", 1)[1].split("\ndef ", 1)[0]


def test_only_the_payer_takes_everything_or_closes_it():
	for name in ("prepare", "download", "close", "keep"):
		assert "_payer()" in _body(name, HERE), name
	assert "roles.require()" in _body("_payer", HERE) and "_is_payer()" in _body("_payer", HERE)
	assert "check_password(frappe.session.user" in _body("close", HERE)
	assert "roles.require()" in _body("state", HERE)


def test_the_download_is_whole_and_never_half_made():
	build = _body("build", HERE)
	assert "_database(zipped)" in build and "_records(zipped)" in build and "_files(zipped)" in build
	assert ".part" in build and "os.replace(part, path)" in build
	assert 'if old != name and not old.endswith(".part")' in build
	assert "new_backup(ignore_files=True, force=True)" in _body("_database", HERE)
	assert 'send_private_file(f"closing/{held.export_file}")' in _body("download", HERE)
	for secret in ("OAuth Bearer Token", "OAuth Authorization Code", "Token Cache"):
		assert f'"{secret}"' in HERE.split("LEFT_OUT = (", 1)[1].split(")", 1)[0], secret
	assert "limit %s offset %s" in _body("_records", HERE), "a large table is read in batches"


def test_nothing_without_a_closing_day_is_ever_closed():
	due = _body("due", THERE)
	assert '["closing_on", "is", "set"]' in due, "frappe reads a missing date as 0001-01-01"
	assert '["status", "in", list(OPEN)]' in due and 'runner.start(slug, "Archive")' in due
	assert "site.is_admin()" in due
	assert '"onedesk.one_admin.closing.due"' in HOOKS


def test_closing_waits_out_its_notice_and_can_be_undone_until_then():
	ask = _body("ask", THERE)
	assert "add_days(today(), NOTICE_DAYS)" in ask and "tenant.status not in OPEN" in ask
	assert "tenant.is_house" in ask and "_renewal(tenant, ends=True)" in ask
	keep = _body("keep", THERE)
	assert "tenant.status not in OPEN" in keep and "_renewal(tenant, ends=False)" in keep
	ladder = (tree.APP / "one_admin" / "ladder.py").read_text()
	assert "NOTICE_DAYS = 14" in ladder
	legal = (tree.APP / "one_legal" / "legal.py").read_text()
	assert "{NOTICE_DAYS} days" in legal and 'DAYS["Archived"]} days later' in legal


def test_the_account_hears_only_from_the_workspace_itself():
	for name in ("close", "withdraw_closing"):
		body = _body(name, PROXY)
		assert "caller().name" in body, name
	assert '"closing": closing.when(_tenant_doc(tenant))' in PROXY
	account = (tree.APP / "one" / "account.py").read_text()
	assert '"closing_on": (said.get("closing") or {}).get("closing_on")' in account


def test_everybody_concerned_is_told():
	here = (tree.APP / "one" / "notifications.py").read_text()
	for name in ("Full Download Ready", "Workspace Closing", "Workspace Staying Open"):
		assert f'_lt("{name}")' in here, name
	there = (tree.APP / "one_admin" / "notifications.py").read_text()
	for name in ("Workspace Asked to Close", "Workspace Closed"):
		assert f'_lt("{name}")' in there, name
	assert 'if tenant.get("closing_on"):\n\t\t\t# Closed because they asked' in TELL
	for name in ("close", "keep"):
		assert 'sender="Administrator"' in _body(name, HERE), "the payer is told too"


def test_a_closed_workspace_is_not_asked_to_pay():
	accounts = (tree.APP / "one_admin" / "accounts.py").read_text()
	assert 'owing = one.status in FALLS and not one.get("closing_on")' in accounts
