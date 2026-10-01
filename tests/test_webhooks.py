"""Webhooks (one/webhooks.py): an administrator's, on the kinds they may
read, sending only fields they may read, over https to a public address,
checked again on every hop when sent. These read the code that says so."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

SOURCE = (tree.APP / "one" / "webhooks.py").read_text()
HOOKS = (tree.APP / "hooks.py").read_text()


def _body(name: str) -> str:
	return SOURCE.split(f"def {name}(", 1)[1].split("\ndef ", 1)[0]


def test_only_an_administrator_and_only_on_what_they_read():
	assert '"Webhook": "onedesk.one.webhooks.has_permission"' in HOOKS
	assert '"Webhook Request Log": "onedesk.one.webhooks.has_permission"' in HOOKS
	assert '"Webhook": "onedesk.one.webhooks.query"' in HOOKS
	assert '"Webhook Request Log": "onedesk.one.webhooks.log_query"' in HOOKS
	allowed = _body("has_permission")
	assert "roles.administers(user)" in allowed and "_kinds()" in allowed
	assert 'ptype not in ("read", "report", None)' in allowed, "the log is read only"
	assert 'return "1=0"' in _body("query") and 'return "1=0"' in _body("log_query")
	assert "write" not in SOURCE.split("GRANTS = ", 1)[1].split("\n", 1)[0].split("LOG:", 1)[1]


def test_what_a_workspace_webhook_may_send_and_where():
	assert '"Webhook": {"validate": "onedesk.one.webhooks.validate"}' in HOOKS
	check = _body("validate")
	assert "layer.held()" in check and "doctype not in _kinds()" in check
	assert "REFUSED_MODULES" in check
	assert '(doc.condition or "").strip()' in check, "it decides by no code"
	assert "doc.is_dynamic_url = 0" in check and "doc.background_jobs_queue = None" in check
	assert "FIELD.fullmatch(tag)" in check and "_unseen(doctype)" in check
	address = _body("_check_address")
	assert 'urlparse(url).scheme != "https"' in address and "_guard_url(url)" in address


def test_every_send_is_guarded_on_every_hop():
	install = _body("install")
	assert "_send_guarded_request" in install and "webhook.send_webhook_request = guarded" in install
	assert '"onedesk.one.webhooks.install"' in HOOKS.split("before_request = ", 1)[1].split("\n", 1)[0]
	assert 'before_job = ["onedesk.one.webhooks.install"]' in HOOKS


def test_the_administrators_hear_when_calls_give_up():
	assert '"onedesk.one.webhooks.failing"' in HOOKS
	failing = _body("failing")
	assert '"status": "Exhausted"' in failing and 'notify.notify(\n\t\t"Webhooks Failing"' in failing
	types = (tree.APP / "one" / "notifications.py").read_text()
	assert '_lt("Webhooks Failing")' in types


def test_the_sidebar_reaches_both():
	sidebar = json.loads((tree.APP / "one" / "sidebar" / "one" / "one.json").read_text())
	links = {one["link_to"]: one["label"] for one in sidebar["items"] if one.get("link_type") == "DocType"}
	assert links["Webhook"] == "Webhooks" and links["Webhook Request Log"] == "Webhook Calls"
