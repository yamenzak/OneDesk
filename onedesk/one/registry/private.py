"""A private app's manifest.py (docs/PRIVATE-APPS.md): the App a Frappe app
made for some workspaces declares at its package root, the way One's own
apps do, with the fields a private app may set. It is read, never imported:
the release build and OneAdmin run none of a private app's code, so every
value is a literal (a word may be wrapped in `_lt`, a reason in `Kept`, the
roles in `Roles`) and anything else is refused. Pure."""

import ast
from pathlib import Path

from onedesk.one.registry import Invalid, _check, apps
from onedesk.one.registry.model import App, Kept, Roles

SAYS = ("id", "name", "kind", "module", "line", "mark", "needs", "kept", "roles", "plan")
MADE = {"Kept": Kept, "Roles": Roles}
TUPLES = ("needs", "plan")


def parsed(source: str, where: str = "manifest.py") -> App:
	"""The App a private app's manifest source declares as `APP = App(...)`,
	checked against One's own apps by the registry's own rules."""
	try:
		body = ast.parse(source).body
	except SyntaxError as raised:
		raise Invalid(f"{where}: {raised.msg}") from raised
	call = next((node.value for node in body if isinstance(node, ast.Assign) and [getattr(one, "id", None) for one in node.targets] == ["APP"]), None)
	if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == "App"):
		raise Invalid(f"{where}: APP must be App(...)")
	if call.args or any(one.arg is None for one in call.keywords):
		raise Invalid(f"{where}: App(...) takes its fields by name")
	said = {}
	for one in call.keywords:
		if one.arg not in SAYS:
			raise Invalid(f"{where}: {one.arg!r} is not something a private app says; it says {', '.join(SAYS)}")
		said[one.arg] = _value(one.value, f"{where}: {one.arg}")
	for key in TUPLES:
		if key in said:
			said[key] = _strings(said[key], f"{where}: {key}")
	if not isinstance(said.get("id"), str) or not isinstance(said.get("name"), str) or not said["name"]:
		raise Invalid(f"{where}: a private app says its id and its name")
	if said.pop("kind", "app") != "app":
		raise Invalid(f"{where}: a private app's kind is app")
	for key in ("module", "line", "mark"):
		if not isinstance(said.get(key, ""), str):
			raise Invalid(f"{where}: {key} is words")
	if not isinstance(said.get("kept", Kept("")), Kept) or not isinstance(said.get("roles", Roles()), Roles):
		raise Invalid(f"{where}: kept is a Kept(...) and roles a Roles(...)")
	app = App(**said, kind="app", ui="native", private=True)
	_check([app, *apps()])
	return app


def at(package: Path) -> App | None:
	"""The App in `package/manifest.py`, its id the package's; None when
	the package has no manifest."""
	path = Path(package) / "manifest.py"
	if not path.is_file():
		return None
	app = parsed(path.read_text(encoding="utf-8"), f"{path.parent.name}/manifest.py")
	if app.id != path.parent.name:
		raise Invalid(f"{path.parent.name}/manifest.py: id is {app.id!r}, the package is {path.parent.name!r}")
	return app


def card(app: App) -> dict:
	"""What its card in Apps shows, and what a release tells OneAdmin."""
	return {"app": app.id, "title": app.name, "said": app.line, "icon": app.mark}


def _value(node: ast.AST, where: str):
	if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
		if node.func.id == "_lt" and len(node.args) == 1 and not node.keywords:
			text = _value(node.args[0], where)
			if isinstance(text, str):
				return text
		if node.func.id in MADE:
			args = [_value(one, where) for one in node.args]
			kwargs = {one.arg: _value(one.value, where) for one in node.keywords if one.arg}
			if len(kwargs) != len(node.keywords):
				raise Invalid(f"{where} is not a literal")
			try:
				made = MADE[node.func.id](*args, **kwargs)
			except TypeError as raised:
				raise Invalid(f"{where}: {raised}") from raised
			if node.func.id == "Roles":
				return Roles(*(_strings(getattr(made, one), where) for one in ("user", "manager")))
			if not isinstance(made.why, str):
				raise Invalid(f"{where}: a Kept says why in words")
			return Kept(made.why, _strings(made.when, where))
		raise Invalid(f"{where} is not a literal")
	try:
		return ast.literal_eval(node)
	except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError) as raised:
		raise Invalid(f"{where} is not a literal") from raised


def _strings(value, where: str) -> tuple[str, ...]:
	if not isinstance(value, (list, tuple)) or not all(isinstance(one, str) for one in value):
		raise Invalid(f"{where} is a list of words")
	return tuple(value)
