"""Point 10: every notification One sends goes through one/notify.py.

A notification sent any other way has text an administrator cannot change and
channels nobody can choose, so nothing else in OneDesk may call
`frappe.sendmail`, write a Notification Log, or enqueue one. Each type a module
sends is one file in `onedesk/notifications/`, and each name sent is declared.
"""

import ast
import functools
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import tree

NOTIFY = tree.APP / "one" / "notify.py"
HOOKS = tree.hooks()


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
	"""Every notification file, read in its layout (onedesk/notifications/)."""
	return tree.notifications()


def _layout():
	import importlib.util

	spec = importlib.util.spec_from_file_location("layout", tree.APP / "notifications" / "layout.py")
	layout = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(layout)
	return layout


def test_every_notification_is_one_file_in_one_layout():
	"""One folder, a file a type, under the module that sends it, named for
	the type and written exactly as the layout writes it, so the header keys
	are always in one order and a message always wraps the same way."""
	layout = _layout()
	modules = {path.name for path in tree.APP.iterdir() if (path / "__init__.py").exists()}
	for name, one in _declared().items():
		path = one["file"]
		assert one["module"] in modules, f"{name} is under {one['module']}, which is no module"
		if path.name == "notifications.py":
			typed = {key: value for key, value in one.items() if key not in ("module", "file", *layout.MODULE_KEYS)}
			assert layout.read(layout.write(typed)) == typed, f"{name} in {path} is not in the one layout"
			continue
		assert path.name == layout.slug(name), f"{name} is in {path.name}"
		text = path.read_text(encoding="utf-8")
		assert text == layout.write(layout.read(text)), f"{path.name} is not in the one layout"
	assert re.search(r'one_notification_types = \["onedesk\.notifications\.TYPES"\]', HOOKS)


def test_nothing_declares_a_notification_anywhere_else():
	"""A list of types in a module's own file is a second place to look, but
	for a module on its way to ready, whose notifications.py replaces its
	files (docs/READY.md, A module's folder)."""
	moved = {path for _folder, path in tree.declared_notifications()}
	stray = [
		str(path.relative_to(tree.APP))
		for path in _python()
		if path not in moved
		and (path.name == "notifications.py" or re.search(r'"subject": _lt\(', path.read_text(encoding="utf-8")))
	]
	assert not stray, stray


KEYS = {
	"name", "app", "about", "subject", "message", "roles", "email", "push", "email_default",
	"push_default", "outside", "required", "always_mailed", "words", "rule", "mailed_by", "switch",
	"replaces", "replaces_rules", "starts_as", "to", "button", "from_one", "follows", "oneai", "notification",
}  # fmt: skip


def test_every_type_says_what_it_needs():
	for name, one in _declared().items():
		extra = {"module", "file"} | (set(_layout().MODULE_KEYS) if one["file"].name == "notifications.py" else set())
		assert set(one) - extra <= KEYS, f"{name}: {sorted(set(one) - KEYS - extra)}"
		upstream = one.get("mailed_by") or one.get("words")
		assert {"name", "app", "about"} <= set(one), name
		assert bool(one.get("subject")) != bool(upstream), name
		assert not (one.get("outside") and one.get("push_default")), (
			f"{name} goes outside and cannot be pushed"
		)
		assert not (one.get("mailed_by") and one.get("rule")), (
			f"{name}: a rule is told, not mailed by its app"
		)
		assert not one.get("rule") or one.get("words"), f"{name}: a rule is in its app's words"
		for doctype, field in [
			*(one.get("replaces") or ()),
			*filter(None, [one.get("switch"), one.get("starts_as")]),
		]:
			assert doctype.endswith("Settings") and field, name
		for rule in one.get("replaces_rules") or ():
			assert isinstance(rule, str) and rule and not rule.endswith("Settings"), name


def test_every_type_says_when_and_to_whom_the_same_way():
	"""One way of saying a type (docs/WORDING.md): `about` is when it is sent,
	one sentence from the reader's side, never "the same" as another; `to` is
	who, apart, because on a person's own page it is always them."""
	opening = ("When ", "On ", "Once ", "Every ", "Before ", "Shortly ", "The day ", "As often ")
	for name, one in _declared().items():
		assert one["about"].startswith(opening), f"{name}: {one['about']}"
		assert "the same" not in one["about"].lower(), name
		assert one.get("to"), f"{name} does not say who it is sent to"
		assert "Sent to" not in one["about"], f"{name}: who it goes to is `to`"


def test_a_twin_follows_a_kind_of_its_own_app():
	declared = _declared()
	for name, one in declared.items():
		if one.get("follows"):
			followed = declared[one["follows"]]
			assert followed["app"] == one["app"] and not followed.get("follows"), name
			assert followed.get("roles") == one.get("roles"), name


@functools.cache
def _sent() -> tuple:
	"""Every `notify.notify(...)` and `notify.mail(...)`: which way, and the
	type names its first argument can be (a name, or `a if x else b`)."""
	return tuple(_sends())


def _sends():
	for path in _python():
		if "notify" not in tree.text(path):
			continue
		for node in tree.walked(path):
			func = getattr(node, "func", None)
			if (
				isinstance(node, ast.Call)
				and isinstance(func, ast.Attribute)
				and func.attr in ("notify", "mail")
				and getattr(func.value, "id", None) == "notify"
			):
				first = node.args[0]
				if path == tree.APP / "one" / "tell.py" and getattr(first, "id", None) == "carried":
					yield func.attr, [name for name, one in _declared().items() if one.get("rule")]
					continue
				if isinstance(first, ast.Attribute) and getattr(first.value, "id", None) == "self":
					yield func.attr, _constants(path, first.attr)
					continue
				names = [first.body, first.orelse] if isinstance(first, ast.IfExp) else [first]
				assert all(isinstance(one, ast.Constant) for one in names), (
					f"{path.name}:{node.lineno} names its type in a variable, so it cannot be checked"
				)
				yield func.attr, [one.value for one in names]


def _constants(path, attr: str) -> list[str]:
	"""Every string a module assigns to `attr`, alone or in a tuple."""
	found = []
	for node in tree.walked(path):
		if not isinstance(node, ast.Assign):
			continue
		for target in node.targets:
			pairs = (
				zip(target.elts, node.value.elts, strict=True)
				if isinstance(target, ast.Tuple) and isinstance(node.value, ast.Tuple)
				else [(target, node.value)]
			)
			found += [
				value.value
				for name, value in pairs
				if getattr(name, "id", None) == attr and isinstance(value, ast.Constant) and value.value
			]
	assert found, f"{path.name} never says what {attr} is"
	return found


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
