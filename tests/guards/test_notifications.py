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


def sends_elsewhere(source: str) -> list[str]:
	"""The ways of sending past one/notify.py a source uses. Pure."""
	return [pattern.pattern for pattern in FORBIDDEN if pattern.search(source)]


def test_nothing_else_sends():
	found = [
		f"{path.relative_to(tree.APP)}: {pattern}"
		for path in _python()
		for pattern in sends_elsewhere(path.read_text(encoding="utf-8"))
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


def out_of_layout(declared: dict, layout, modules: set[str], hooks: str) -> list[str]:
	"""The types not under a module, not in their own file or not written as
	the layout writes them, and hooks not naming the types. Pure."""
	wrong = []
	for name, one in declared.items():
		path = one["file"]
		if one["module"] not in modules:
			wrong.append(f"{name} is under {one['module']}, which is no module")
			continue
		if path.name == "notifications.py":
			typed = {key: value for key, value in one.items() if key not in ("module", "file", *layout.MODULE_KEYS)}
			if layout.read(layout.write(typed)) != typed:
				wrong.append(f"{name} in {path} is not in the one layout")
			continue
		if path.name != layout.slug(name):
			wrong.append(f"{name} is in {path.name}")
			continue
		text = path.read_text(encoding="utf-8")
		if text != layout.write(layout.read(text)):
			wrong.append(f"{path.name} is not in the one layout")
	if not re.search(r'one_notification_types = \["onedesk\.notifications\.TYPES"\]', hooks):
		wrong.append("hooks.py does not name onedesk.notifications.TYPES")
	return wrong


def test_every_notification_is_one_file_in_one_layout():
	"""One folder, a file a type, under the module that sends it, named for
	the type and written exactly as the layout writes it, so the header keys
	are always in one order and a message always wraps the same way."""
	modules = {path.name for path in tree.APP.iterdir() if (path / "__init__.py").exists()}
	wrong = out_of_layout(_declared(), _layout(), modules, HOOKS)
	assert not wrong, wrong


def declares_elsewhere(path: Path, source: str, moved: set) -> bool:
	"""Whether a file lists notification types outside onedesk/notifications/. Pure."""
	return path not in moved and (path.name == "notifications.py" or bool(re.search(r'"subject": _lt\(', source)))


def test_nothing_declares_a_notification_anywhere_else():
	"""A list of types in a module's own file is a second place to look, but
	for a module on its way to ready, whose notifications.py replaces its
	files (docs/READY.md, A module's folder)."""
	moved = {path for _folder, path in tree.declared_notifications()}
	stray = [str(path.relative_to(tree.APP)) for path in _python() if declares_elsewhere(path, path.read_text(encoding="utf-8"), moved)]
	assert not stray, stray


KEYS = {
	"name", "app", "about", "subject", "message", "roles", "email", "push", "email_default",
	"push_default", "outside", "required", "always_mailed", "words", "rule", "mailed_by", "switch",
	"replaces", "replaces_rules", "starts_as", "to", "button", "from_one", "follows", "oneai", "notification",
}  # fmt: skip


def wanting(declared: dict, module_keys) -> list[str]:
	"""The types with a key nobody reads or without what they need. Pure."""
	wrong = []
	for name, one in declared.items():
		extra = {"module", "file"} | (set(module_keys) if one["file"].name == "notifications.py" else set())
		upstream = one.get("mailed_by") or one.get("words")
		pairs = [*(one.get("replaces") or ()), *filter(None, [one.get("switch"), one.get("starts_as")])]
		said = [
			(set(one) - extra <= KEYS, f"{name}: {sorted(set(one) - KEYS - extra)}"),
			({"name", "app", "about"} <= set(one), name),
			(bool(one.get("subject")) != bool(upstream), name),
			(not (one.get("outside") and one.get("push_default")), f"{name} goes outside and cannot be pushed"),
			(not (one.get("mailed_by") and one.get("rule")), f"{name}: a rule is told, not mailed by its app"),
			(not one.get("rule") or one.get("words"), f"{name}: a rule is in its app's words"),
			*((doctype.endswith("Settings") and field, name) for doctype, field in pairs),
			*((isinstance(rule, str) and rule and not rule.endswith("Settings"), name) for rule in one.get("replaces_rules") or ()),
		]
		wrong += [message for held, message in said if not held]
	return wrong


def test_every_type_says_what_it_needs():
	wrong = wanting(_declared(), _layout().MODULE_KEYS)
	assert not wrong, wrong


OPENING = ("When ", "On ", "Once ", "Every ", "Before ", "Shortly ", "The day ", "As often ")


def said_otherwise(declared: dict) -> list[str]:
	"""The types whose `about` or `to` breaks the one way of saying them. Pure."""
	wrong = []
	for name, one in declared.items():
		about = one.get("about") or ""
		if not about.startswith(OPENING):
			wrong.append(f"{name}: {about}")
		if "the same" in about.lower():
			wrong.append(f"{name} says it is the same as another")
		if not one.get("to"):
			wrong.append(f"{name} does not say who it is sent to")
		if "Sent to" in about:
			wrong.append(f"{name}: who it goes to is `to`")
	return wrong


def test_every_type_says_when_and_to_whom_the_same_way():
	"""One way of saying a type (docs/WORDING.md): `about` is when it is sent,
	one sentence from the reader's side, never "the same" as another; `to` is
	who, apart, because on a person's own page it is always them."""
	wrong = said_otherwise(_declared())
	assert not wrong, wrong


def stray_twins(declared: dict) -> list[str]:
	"""The twins following a type of another app, a twin, or other roles. Pure."""
	wrong = []
	for name, one in declared.items():
		if one.get("follows"):
			followed = declared[one["follows"]]
			if not (followed["app"] == one["app"] and not followed.get("follows") and followed.get("roles") == one.get("roles")):
				wrong.append(name)
	return wrong


def test_a_twin_follows_a_kind_of_its_own_app():
	wrong = stray_twins(_declared())
	assert not wrong, wrong


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


def undeclared(sent, declared: dict) -> list[str]:
	"""The type names sent that no file declares. Pure."""
	return sorted({name for _way, names in sent for name in names} - set(declared))


def test_every_type_sent_is_declared():
	sent = _sent()
	assert {name for _way, names in sent for name in names}, "nothing sends through notify"
	missing = undeclared(sent, _declared())
	assert not missing, f"sent but not declared: {missing}"


def pushed_outside(sent, declared: dict) -> list[str]:
	"""The types going to outside addresses that are not mailed. Pure."""
	return [name for way, names in sent for name in names if way != "mail" and declared[name].get("outside")]


def test_outside_types_are_mailed_and_the_rest_notified():
	wrong = pushed_outside(_sent(), _declared())
	assert not wrong, f"{wrong} go to outside addresses, so they are mailed"


def unnamed_slots(declared: dict) -> list[str]:
	"""The types whose default subject or message has a slot like `{0}`. Pure."""
	return [f"{name} {key}" for name, one in declared.items() for key in ("subject", "message") if re.search(r"\{\d*\}", one.get(key) or "")]


def test_slots_are_named():
	"""A default text's slots are names, never `{0}`: the administrator edits
	it as `{{ name }}`, and a number would not say what goes there."""
	wrong = unnamed_slots(_declared())
	assert not wrong, f"an unnamed slot: {wrong}"


def test_the_notification_rules_catch_their_examples(tmp_path):
	assert sends_elsewhere("frappe.sendmail(recipients=[x])") == [r"frappe\.sendmail\("]
	assert sends_elsewhere("notify.notify('x', to)") == []
	layout = _layout()
	good = {"name": "Leave Approved", "app": "OneHR", "about": "When a leave is approved.", "to": "The employee", "subject": "Approved {{ name }}"}
	path = tmp_path / layout.slug(good["name"])
	path.write_text(layout.write(good), encoding="utf-8")
	hooks = 'one_notification_types = ["onedesk.notifications.TYPES"]'
	assert out_of_layout({good["name"]: {**good, "module": "one_hr", "file": path}}, layout, {"one_hr"}, hooks) == []
	assert out_of_layout({good["name"]: {**good, "module": "gone", "file": path}}, layout, {"one_hr"}, hooks) == ["Leave Approved is under gone, which is no module"]
	assert out_of_layout({}, layout, set(), "") == ["hooks.py does not name onedesk.notifications.TYPES"]
	path.write_text(layout.write(good) + "\n\n", encoding="utf-8")
	assert out_of_layout({good["name"]: {**good, "module": "one_hr", "file": path}}, layout, {"one_hr"}, hooks) == [f"{path.name} is not in the one layout"]
	assert declares_elsewhere(Path("one_hr/leave.py"), 'TYPES = [{"subject": _lt("Hi")}]', set())
	assert not declares_elsewhere(Path("one_hr/notifications.py"), "", {Path("one_hr/notifications.py")})
	declared = {"x": {**good, "file": Path("x.md")}}
	assert wanting(declared, ()) == []
	assert wanting({"x": {**good, "file": Path("x.md"), "colour": "red"}}, ()) == ["x: ['colour']"]
	assert wanting({"x": {**good, "file": Path("x.md"), "outside": 1, "push_default": 1}}, ()) == ["x goes outside and cannot be pushed"]
	assert said_otherwise(declared) == []
	assert said_otherwise({"x": {**good, "about": "Sent to the employee.", "to": ""}}) == [
		"x: Sent to the employee.",
		"x does not say who it is sent to",
		"x: who it goes to is `to`",
	]
	twins = {"a": {"app": "OneHR", "roles": ["HR"]}, "b": {"app": "OneCRM", "roles": ["HR"], "follows": "a"}}
	assert stray_twins(twins) == ["b"]
	assert stray_twins({**twins, "b": {**twins["b"], "app": "OneHR"}}) == []
	assert undeclared([("notify", ["x", "y"])], {"x": {}}) == ["y"]
	assert pushed_outside([("notify", ["x"]), ("mail", ["x"])], {"x": {"outside": 1}}) == ["x"]
	assert unnamed_slots({"x": {"subject": "Hi {0}", "message": "Hi {{ name }}"}}) == ["x subject"]
