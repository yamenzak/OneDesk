"""OneMail: addresses on the mail domain, and the mail that arrives at them."""

import ast
import hashlib
import hmac
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

MAIL = tree.APP / "one_mail"
WORKER = (tree.ROOT / "deploy" / "mail" / "worker.js").read_text()
HOOKS = (tree.APP / "hooks.py").read_text()


def _load(path: Path, names: tuple, **extra) -> dict:
	space = dict(extra)
	for node in ast.parse(path.read_text()).body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") in names:
			exec(ast.unparse(node), space)
		if isinstance(node, ast.FunctionDef) and node.name in names:
			exec(ast.unparse(node), space)
	return space


def test_an_address_belongs_to_the_workspace_after_its_last_dot():
	space = _load(MAIL / "addresses.py", ("NAME", "RESERVED", "is_name", "is_workspace_name"), re=re)
	mine = space["is_workspace_name"]
	assert mine("acme", "acme") and mine("ahmad.acme", "acme") and mine("AHMAD.acme", "acme")
	assert not mine("ahmad.other", "acme")
	assert not mine("x.ahmad.acme", "acme"), "a person's part has no dot"
	assert not mine("postmaster.acme", "acme"), "reserved"
	assert not mine("acme", ""), "no workspace, no address"
	assert not mine(".acme", "acme")


def test_a_notice_is_believed_only_signed_and_fresh():
	space = _load(MAIL / "inbound.py", ("SKEW", "signed", "fresh", "name_in"), hmac=hmac, hashlib=hashlib, time=__import__("time"))
	body = b'{"key":"mail/in/1~acme.eml"}'
	expected = hmac.new(b"s", b"100." + body, hashlib.sha256).hexdigest()
	assert space["signed"]("s", "100", body) == expected
	assert space["fresh"]("1000", now=1100) and not space["fresh"]("1000", now=2000)
	assert not space["fresh"]("soon") and not space["fresh"](None)


def test_the_key_says_which_address_a_message_came_to():
	name_in = _load(MAIL / "inbound.py", ("name_in",))["name_in"]
	assert name_in("mail/in/20260924-uuid~ahmad.acme.eml") == "ahmad.acme"
	assert name_in("tenants/acme/mail/in/1-u~acme.eml") == "acme"
	assert name_in("mail/in/1-u.eml") is None
	assert "~${bare}.eml" in WORKER, "the Worker writes what name_in reads"


def test_a_thread_is_a_message_id_never_a_subject():
	space = _load(MAIL / "threads.py", ("MESSAGE_ID", "ids", "pick"), re=re)
	assert space["ids"]("<a@x> <b@y>\n <c@z>") == ["a@x", "b@y", "c@z"]
	assert space["pick"](["a@x", "b@y"], {"b@y": "root@x"}) == "root@x"
	assert space["pick"](["a@x"], {}) is None
	assert "subject" not in (MAIL / "threads.py").read_text().split('"""', 2)[2].lower()


def test_mail_is_read_from_r2_every_minute_whatever_the_notice_did():
	assert '"* * * * *": ["onedesk.one_mail.inbound.sweep"]' in HOOKS
	source = (MAIL / "inbound.py").read_text()
	assert "raise frappe.PermissionError" in source and "hmac.compare_digest" in source
	assert '{"one_raw_key": key}' in source, "taking one twice is taking it once"


def test_admin_names_only_a_workspaces_own_addresses():
	proxy = (tree.APP / "one_admin" / "proxy.py").read_text()
	assert "addresses.is_workspace_name(one, tenant.slug)" in proxy
	assert "storage.mail_waiting(_tenant_doc(caller()), after)" in proxy


def test_kv_values_are_sent_as_multipart_not_a_form():
	source = (tree.APP / "one_admin" / "cloudflare.py").read_text()
	assert 'files={"value": (None, data), "metadata": (None, "{}")}' in source
	assert 'data={"value": data' not in source
