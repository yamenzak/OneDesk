"""hooks.py's per-module lists, built from the registry: what each folder's
files declare by convention, what its manifest names in `hooks`, and its
`settle` steps. Pure: files are read, never imported, so hooks.py loads
without importing a module's code."""

import ast
from functools import cache
from pathlib import Path

from onedesk.one import registry

CONVENTIONS = {
	"one_abilities": ("abilities", None, None),
	"one_ai_page": ("ai", "page", None),
	"one_ai_suggestions": ("ai", "SUGGESTIONS", None),
	"one_ai_reads": ("ai", "READS", "each"),
	"one_ai_suggests": ("ai", "SUGGESTS", "each"),
	"one_record_heads": ("heads", "HEADS", None),
	"one_measures": ("heads", "MEASURES", None),
	"one_verbs": ("heads", "VERBS", None),
	"one_charts": ("heads", "CHARTS", None),
	"one_calendar_layers": ("calendar", "LAYERS", None),
	"one_portal": ("portal", None, None),
}
"""hook: (file stem, the name it must define or None for the module itself,
"each" when the name is a tuple of tools to list one by one: a tool of the
file itself, or "ai_payroll.payroll_changes" for one in a file beside it)."""

ENGINES = {"one_portal": "one_portal"}
"""A hook's own engine, whose file of that name is the engine, not a part."""


IRREGULAR = (
	"one_ai_reader",
	"one_ai_workspace",
	"one_ai_actions",
	"automation_actions",
	"one_homes",
	"one_record_tabs",
	"one_record_notices",
	"one_slide_loaded",
	"one_slide_saving",
	"one_slide_rows",
)
"""Hooks one app or a few fill, each named in that app's manifest `hooks`."""


def derived() -> tuple[str, ...]:
	"""Every hook hooks.py builds from the registry, but the settle lists."""
	return (*CONVENTIONS, *IRREGULAR)


def hook(name: str) -> list[str]:
	"""Every entry for one hook, folder by folder in the rail's order."""
	found = []
	stem, attr, each = CONVENTIONS.get(name, (None, None, None))
	for app in registry.apps():
		for place in _places(app):
			if stem and ENGINES.get(name) != place:
				found += _declared(place, stem, attr, each)
		found += [f"onedesk.{app.id}.{path}" for path in app.hooks.get(name, ())]
	return found


def heirs() -> dict[str, list[str]]:
	"""one_module_heirs: each Frappe module an app owns, to the app whose
	records they are reached in (one/outside.py)."""
	return {module: [app.name] for app in registry.apps() for module in app.owns}


def settles(install: bool) -> list[str]:
	"""after_sync (install) or after_migrate: every app's steps in the rail's
	order, then every app's `last` ones."""
	steps = [(one.last, f"onedesk.{app.id}.{one.path}") for app in registry.apps() for one in app.settle if install or not one.install_only]
	return [path for last, path in steps if not last] + [path for last, path in steps if last]


def _places(app) -> list[str]:
	return [app.id, *(f"{app.id}.{part}" for part in app.parts)]


def _declared(place: str, stem: str, attr: str | None, each: str | None) -> list[str]:
	path = registry.FOLDERS.joinpath(*place.split("."), f"{stem}.py")
	if not path.exists():
		return []
	module = f"onedesk.{place}.{stem}"
	if attr is None:
		return [module]
	names = _names(path)
	if attr not in names:
		return []
	if each:
		return [f"onedesk.{place}.{tool}" if "." in tool else f"{module}.{tool}" for tool in names[attr]]
	return [f"{module}.{attr}"]


@cache
def _names(path: Path) -> dict:
	"""A file's top-level names; a tuple of strings is kept as its value."""
	said = {}
	for node in ast.parse(path.read_text(encoding="utf-8")).body:
		if isinstance(node, ast.FunctionDef | ast.ClassDef):
			said[node.name] = None
		elif isinstance(node, ast.Assign | ast.AnnAssign):
			targets = node.targets if isinstance(node, ast.Assign) else [node.target]
			value = None
			if isinstance(node.value, ast.Tuple) and all(isinstance(one, ast.Constant) for one in node.value.elts):
				value = tuple(one.value for one in node.value.elts)
			for target in targets:
				if isinstance(target, ast.Name):
					said[target.id] = value
	return said
