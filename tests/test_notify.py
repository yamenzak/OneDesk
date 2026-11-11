"""How one/notify.py lays a notification out, lets it be edited, pushes it,
rules it and brings in the apps' own mails. The guards on who sends and what
is declared are in tests/guards/test_notifications.py."""

import ast
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

from tests.guards.test_notifications import _declared, _layout

NOTIFY = tree.APP / "one" / "notify.py"
HOOKS = (tree.APP / "hooks.py").read_text(encoding="utf-8")


def test_a_layout_reads_back_what_it_writes():
	layout = _layout()
	one = {
		"name": "Invitation",
		"app": "One",
		"roles": ("HR Manager", "HR User"),
		"about": "When an administrator invites someone: today.",
		"to": "The person invited",
		"outside": True,
		"replaces": (("HR Settings", "send_birthday_reminders"), ("Stock Settings", "reorder_email_notify")),
		"subject": "{inviter} invited you",
		"message": '<b>{inviter}</b> invited you.<br><br><a href="{link}">Choose your password</a><br><br>'
		+ "The link works for {days} days. " * 6,
	}
	one["message"] = one["message"].strip()
	assert layout.read(layout.write(one)) == one
	assert layout.only_slots("{reasons}") and not layout.only_slots("{task} is late")


def _jinja():
	space = {"re": re}
	for fn in ("raw", "jinja"):
		for node in ast.parse(NOTIFY.read_text(encoding="utf-8")).body:
			if isinstance(node, ast.FunctionDef) and node.name == fn:
				exec(ast.unparse(node), space)
	return space


def test_a_default_becomes_jinja_as_it_is_edited():
	space = _jinja()
	assert space["jinja"]("<b>{who}</b> shared {file}") == "<b>{{ who }}</b> shared {{ file }}"
	assert space["jinja"](None) == ""


def test_raw_keeps_the_untranslated_text():
	class Lazy:
		msg = "{who} shared"

		def __str__(self):
			return "translated"

	assert _jinja()["raw"](Lazy()) == "{who} shared"
	assert _jinja()["raw"]("plain") == "plain"


def test_installed_after_every_migrate():
	after = HOOKS.split("after_migrate = [", 1)[1].split("]", 1)[0]
	assert '"onedesk.one.notify.install"' in after


def test_an_edited_text_sees_nothing_but_its_slots():
	"""Frappe's render_template hands a template frappe.db; an administrator's
	text is rendered in a sandbox with nothing in it but the values sent."""
	source = NOTIFY.read_text(encoding="utf-8")
	assert "frappe.render_template(" not in source
	from jinja2.sandbox import SandboxedEnvironment

	space = {"cache": lambda fn: fn}
	for node in ast.parse(source).body:
		if isinstance(node, ast.FunctionDef) and node.name == "_sandbox":
			exec(ast.unparse(node), space)
	sandbox = space["_sandbox"]()
	assert isinstance(sandbox, SandboxedEnvironment)
	assert sandbox.from_string("{{ frappe }}{{ who }}").render({"who": "Ann"}) == "Ann"


def test_the_workspace_screen_is_for_administrators():
	words = (tree.APP / "one" / "notification_words.py").read_text(encoding="utf-8")
	assert 'if section != "words":' in words
	preview = words.split("def preview_notification(", 1)[1].split("\ndef ", 1)[0]
	assert "roles.require()" in preview
	assert '"Notification Type": {"validate": "onedesk.one.notify.validate"' in HOOKS
	assert '"onedesk.one.ai.rewrite_notification"' in HOOKS and '"onedesk.one.ai.notification_type"' in HOOKS


def _push():
	source = (tree.APP / "one" / "push.py").read_text(encoding="utf-8")
	space = {"urlparse": __import__("urllib.parse", fromlist=["urlparse"]).urlparse}
	for node in ast.parse(source).body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", None) == "SERVICES":
			exec(ast.unparse(node), space)
		if isinstance(node, ast.FunctionDef) and node.name == "allowed_service":
			exec(ast.unparse(node), space)
	return source, space["allowed_service"]


def test_push_goes_only_to_the_browsers_push_services():
	"""The address comes from a browser, so a server that posts wherever it says
	is a server anybody can aim. Only the four push services, over https."""
	_source, allowed = _push()
	assert allowed("https://fcm.googleapis.com/fcm/send/abc")
	assert allowed("https://updates.push.services.mozilla.com/wpush/v2/x")
	assert allowed("https://web.push.apple.com/QAbc")
	assert allowed("https://wns2-db5p.notify.windows.com/w/?token=x")
	for wrong in (
		"http://fcm.googleapis.com/x",
		"https://fcm.googleapis.com.evil.example/x",
		"https://push.apple.com.evil.example/x",
		"https://169.254.169.254/latest",
		"https://localhost/x",
		"",
	):
		assert not allowed(wrong), wrong


def test_push_is_wired_and_its_keys_stay_out_of_the_database():
	source, _allowed = _push()
	logs = HOOKS.split('"Notification Log": {', 1)[1].split("},", 1)[0]
	assert '"after_insert": "onedesk.one.push.pushed"' in logs
	assert "update_site_config(PRIVATE" in source
	assert '"Service-Worker-Allowed": "/"' in source
	worker = source.split('WORKER = """', 1)[1].split('"""', 1)[0]
	assert '"fetch"' not in worker and "'fetch'" not in worker


def _rules():
	source = (tree.APP / "one" / "rules.py").read_text(encoding="utf-8")
	space = {"_": lambda text: text, "readable": lambda doctype: ["description", "status", "name", "owner"]}
	for node in ast.parse(source).body:
		if isinstance(node, ast.FunctionDef) and node.name == "check_text":
			exec(ast.unparse(node), space)
	return source, space["check_text"]


def test_a_workspace_rule_says_only_fields_of_its_record():
	"""Frappe renders a Notification with its template globals; a workspace
	rule's text may name `{{ doc.field }}` and nothing else."""
	_source, check = _rules()
	assert check("ToDo", "New: {{ doc.description }} by {{ doc.owner }}") is None
	assert check("ToDo", None) is None
	for wrong in (
		"{{ frappe.db.get_value('User', 'Administrator', 'api_secret') }}",
		"{{ doc.description | upper }}",
		"{% for x in doc %}{% endfor %}",
		"{{ doc.nosuch }}",
		"{{ doc.__class__ }}",
		"{{ nowdate() }}",
	):
		assert check("ToDo", wrong), wrong


def test_a_workspace_rule_is_held_and_tells_only_who_may_read():
	source, _check = _rules()
	assert '"Notification": "onedesk.one.rules.Rule"' in HOOKS
	hold = source.split("def _hold(", 1)[1].split("\ndef ", 1)[0]
	for kept in (
		'"Filters"',
		'"System Notification"',
		"set_property_after_alert",
		"attach_print",
		"has_permission",
		"send_to_all_assignees",
	):
		assert kept in hold, kept
	recipients = source.split("def get_list_of_recipients(", 1)[1].split("\n\n", 1)[0]
	assert "_may_read" in recipients and "[], []" in recipients
	assert '"DocPerm"' in source


def test_what_erpnext_and_hrms_mail_is_brought_in():
	"""Stage 6: the apps' own switches for what we send are hidden where they
	live, the classes and seams that send it are ours, and a standard rule's
	people here are told rather than mailed."""
	import json

	for name, one in _declared().items():
		for doctype, field in one.get("replaces") or ():
			hidden = [
				setter
				for path in tree.APP.glob("*/custom/*.json")
				for setter in json.loads(path.read_text(encoding="utf-8")).get("property_setters", [])
				if setter.get("doc_type") == doctype
				and setter.get("field_name") == field
				and setter.get("property") == "hidden"
				and str(setter.get("value")) == "1"
			]
			assert hidden, f"{name} replaces {doctype}.{field}, which is still shown"
	for doctype in ("Leave Application", "Expense Claim", "Shift Request", "Interview"):
		assert f'"{doctype}": "onedesk.one_hr.tell.' in HOOKS, doctype
	assert (
		'"erpnext.selling.doctype.customer.customer.send_emails": "onedesk.one_book.tell.credit_limit"'
		in HOOKS
	)
	assert '"on_submit": "onedesk.one_inventory.tell.raised"' in HOOKS
	assert '"Payroll Settings": {"on_update": "onedesk.one.notify.switched"}' in HOOKS
	for job in (
		"birthdays",
		"anniversaries",
		"feedback_due",
		"holidays_weekly",
		"holidays_monthly",
		"interviews_soon",
	):
		assert f'"onedesk.one_hr.tell.{job}"' in HOOKS, job
	rules = (tree.APP / "one" / "rules.py").read_text(encoding="utf-8")
	assert "flags.one_outside_only" in rules.split("def get_list_of_recipients", 1)[1]


def test_no_slot_is_one_of_notifys_own_words():
	"""A slot named for one of `notify()`'s own arguments (`sender`, `link`)
	is taken by the argument and never reaches the text. An outside type is
	only mailed, by `mail()`, which has no such words."""
	tree_ = ast.parse(NOTIFY.read_text(encoding="utf-8"))
	fn = next(node for node in tree_.body if isinstance(node, ast.FunctionDef) and node.name == "notify")
	own = {arg.arg for arg in fn.args.args + fn.args.kwonlyargs}
	wrong = {}
	for name, one in tree.notifications().items():
		if one.get("outside"):
			continue
		found = set(re.findall(r"\{(\w+)\}", f"{one.get('subject', '')} {one.get('message', '')}")) & own
		if found:
			wrong[name] = sorted(found)
	assert not wrong, wrong


UNSUBSCRIBE = tree.APP / "one" / "unsubscribe.py"


def _unsubscribe(*names, **extra) -> dict:
	space = dict(extra)
	for node in ast.parse(UNSUBSCRIBE.read_text(encoding="utf-8")).body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") in names:
			exec(ast.unparse(node), space)
		if isinstance(node, ast.FunctionDef) and node.name in names:
			exec(ast.unparse(node), space)
	return space


def test_a_notification_mail_says_list_unsubscribe_with_one_click():
	with_header = _unsubscribe("with_header")["with_header"]
	url = "https://acme.example/api/method/onedesk.one.unsubscribe.off?email=a%40b&_signature=ff"
	sent = with_header(b"From: a@b\r\nSubject: Hi\r\n\r\nbody\r\nList-Unsubscribe: in the body\r\n", url)
	head, body = sent.split(b"\r\n\r\n", 1)
	assert b"List-Unsubscribe: <" + url.encode() + b">" in head.split(b"\r\n")
	assert b"List-Unsubscribe-Post: List-Unsubscribe=One-Click" in head.split(b"\r\n")
	assert body == b"body\r\nList-Unsubscribe: in the body\r\n", "the body is left as it was"
	again = with_header(sent, url)
	assert again.count(b"List-Unsubscribe:") == 2 and again.count(b"List-Unsubscribe-Post:") == 1
	assert with_header(b"From: a@b\n\nbody\n", url).startswith(b"From: a@b\nList-Unsubscribe: <")


def test_only_a_mail_queued_with_our_method_gets_the_header():
	class Queue(dict):
		__getattr__ = dict.get

	space = _unsubscribe("KIND", "METHOD", "headed", link=lambda email, kind: f"u/{email}/{kind}")
	space["with_header"] = lambda raw, url: raw + url.encode()
	headed, method = space["headed"], space["METHOD"]
	ours = Queue(add_unsubscribe_link=1, unsubscribe_method=method, reference_doctype="Notification Type", reference_name="Leave Approved")
	assert headed(b"m", ours, "a@b") == b"mu/a@b/Leave Approved"
	frappes = Queue(ours, unsubscribe_method="/api/method/frappe.email.queue.unsubscribe")
	assert headed(b"m", frappes, "a@b") == b"m", "frappe's own conversation link has no one-click"
	assert headed(b"m", Queue(ours, add_unsubscribe_link=0), "a@b") == b"m"
	assert headed(b"m", Queue(ours, reference_doctype="Sales Invoice"), "a@b") == b"m"


def test_turn_off_these_emails_is_signed_and_turns_off_one_type():
	"""The link works without signing in, only as signed, and sets the same
	switch NotificationCenter does, for that one type, by email only."""
	source = UNSUBSCRIBE.read_text(encoding="utf-8")
	assert source.count("@frappe.whitelist(allow_guest=True") == 2
	assert source.count("not _signed()") == 2, "both pages check the signature"
	assert "hmac.compare_digest(get_signed_params(params), query)" in source
	assert 'notification_center.choose(kind, "email", on)' in source
	assert '"POST"' in source.split("def off(", 1)[0].rsplit("@frappe.whitelist", 1)[1], "a mail client's one-click is a POST"
	assert "get_unsubcribed_url(KIND, kind, email, method, None)" in source, "frappe's own signed link"
	outbound = (tree.APP / "one_mail" / "outbound.py").read_text(encoding="utf-8")
	assert "unsubscribe.headed(" in outbound


def test_a_mail_that_must_go_carries_no_unsubscribe():
	"""A sign-in link, an invoice, a security notice: an `always_mailed` type,
	or a mail to an address outside (`notify.mail`), is never offered off."""
	source = NOTIFY.read_text(encoding="utf-8")
	send = source.split("def _send(", 1)[1].split("\ndef ", 1)[0]
	assert "if always:" in send and "if off:" in send.split("else:", 1)[1]
	assert "unsubscribe.queued(off) if off and not always else {}" in send
	mail = source.split("\ndef mail(", 1)[1].split("\ndef ", 1)[0]
	assert "unsubscribe" not in mail
	assert "off=unsubscribe.offered(log.for_user, log.type)" in source.split("\ndef mail_log(", 1)[1].split("\ndef ", 1)[0]
	always = source.split("\ndef notify(", 1)[1].split("\ndef ", 1)[0]
	assert "_send(email, lang, name, subject, message, link, record, always=True)" in always
