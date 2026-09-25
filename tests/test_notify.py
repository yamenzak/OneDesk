"""Every notification One sends goes through one/notify.py.

A notification sent any other way has text an administrator cannot change and
channels nobody can choose, so nothing else in OneDesk may call
`frappe.sendmail`, write a Notification Log, or enqueue one. Each type a module
sends is declared in its `notifications.py`, and each name sent is declared.
"""

import ast
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

NOTIFY = tree.APP / "one" / "notify.py"
HOOKS = (tree.APP / "hooks.py").read_text(encoding="utf-8")

#: Reading Notification Log is fine (setup.py asks whether it said something
#: this week); writing one is not. So these are the ways of writing.
FORBIDDEN = (
	re.compile(r"frappe\.sendmail\("),
	re.compile(r"enqueue_create_notification"),
	re.compile(r"make_notification_logs"),
	re.compile(r"[\"']doctype[\"']\s*:\s*[\"']Notification Log[\"']"),
	re.compile(r"new_doc\(\s*[\"']Notification Log[\"']"),
)


def _python():
	for path in tree.APP.rglob("*.py"):
		if path != NOTIFY and "node_modules" not in path.parts:
			yield path


def test_nothing_else_sends():
	found = [
		f"{path.relative_to(tree.APP)}: {pattern.pattern}"
		for path in _python()
		for pattern in FORBIDDEN
		if pattern.search(path.read_text(encoding="utf-8"))
	]
	assert not found, "send through one/notify.py instead:\n" + "\n".join(found)


def _declared() -> dict[str, dict]:
	"""Each module's TYPES, read as literals: `_lt("x")` becomes "x"."""
	paths = re.findall(r'"onedesk\.(\w+)\.notifications\.TYPES"', HOOKS)
	assert paths, "no module declares notification types"
	found = {}
	for module in paths:
		source = (tree.APP / module / "notifications.py").read_text(encoding="utf-8")
		for node in ast.walk(ast.parse(source)):
			if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", None) == "TYPES":
				for one in node.value.elts:
					declared = {
						key.value: (
							value.args[0].value if isinstance(value, ast.Call) else ast.literal_eval(value)
						)
						for key, value in zip(one.keys, one.values, strict=True)
					}
					assert declared["name"] not in found, f"{declared['name']} is declared twice"
					found[declared["name"]] = {**declared, "module": module}
	return found


def test_every_type_says_what_it_needs():
	for name, one in _declared().items():
		assert {"name", "app", "about", "subject"} <= set(one), name
		assert not (one.get("outside") and one.get("push_default")), (
			f"{name} goes outside and cannot be pushed"
		)


def _sent():
	"""Every `notify.notify(...)` and `notify.mail(...)`: which way, and the
	type names its first argument can be (a name, or `a if x else b`)."""
	for path in _python():
		for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
			func = getattr(node, "func", None)
			if (
				isinstance(node, ast.Call)
				and isinstance(func, ast.Attribute)
				and func.attr in ("notify", "mail")
				and getattr(func.value, "id", None) == "notify"
			):
				first = node.args[0]
				names = [first.body, first.orelse] if isinstance(first, ast.IfExp) else [first]
				assert all(isinstance(one, ast.Constant) for one in names), (
					f"{path.name}:{node.lineno} names its type in a variable, so it cannot be checked"
				)
				yield func.attr, [one.value for one in names]


def test_every_type_sent_is_declared():
	declared = _declared()
	sent = {name for _way, names in _sent() for name in names}
	assert sent, "nothing sends through notify"
	assert not sent - set(declared), f"sent but not declared: {sorted(sent - set(declared))}"


def test_outside_types_are_mailed_and_the_rest_notified():
	declared = _declared()
	for way, names in _sent():
		for name in names:
			outside = bool(declared[name].get("outside"))
			assert way == "mail" or not outside, f"{name} goes to outside addresses, so it is mailed"


def test_slots_are_named():
	"""A default text's slots are names, never `{0}`: the administrator edits
	it as `{{ name }}`, and a number would not say what goes there."""
	for name, one in _declared().items():
		for key in ("subject", "message"):
			assert not re.search(r"\{\d*\}", one.get(key) or ""), f"{name} {key} has an unnamed slot"


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
	settings = (tree.APP / "one" / "settings.py").read_text(encoding="utf-8")
	assert '("notification_types", _lt("Notifications"), "bell-ring", "workspace")' in settings
	preview = settings.split("def preview_notification(", 1)[1].split("\ndef ", 1)[0]
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
	assert '"Notification Log": {"after_insert": "onedesk.one.push.pushed"}' in HOOKS
	assert "update_site_config(PRIVATE" in source
	assert '"Service-Worker-Allowed": "/"' in source
	# The worker handles push and clicks, and never a request the page makes.
	worker = source.split('WORKER = """', 1)[1].split('"""', 1)[0]
	assert '"fetch"' not in worker and "'fetch'" not in worker
