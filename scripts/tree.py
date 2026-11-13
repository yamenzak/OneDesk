"""Where the app's own source is, for every tool that walks it, and each
file's text and syntax tree, read once a process and again only when the file
changes."""

import ast
import functools
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "onedesk"

SKIP_DIRS = {"__pycache__", "node_modules", "dist", ".git", "locale"}
SOURCE_SUFFIXES = {".py", ".js", ".ts", ".vue", ".css", ".scss"}


#: Code taken whole from another project, held to that project's own rules and
#: refreshed by copying (frontend/src/sheet/VENDORED.md). What we wrote around
#: it, the page and the shims, is ours and checked like the rest.
VENDORED = (ROOT / "frontend" / "src" / "sheet", ROOT / "frontend" / "src" / "doc", ROOT / "frontend" / "src" / "slide")
OURS_IN_VENDORED = ("WorkbookPage.vue", "DocumentPage.vue", "PresentationPage.vue", "seams.mjs", "shim/")


def vendored(path: Path) -> bool:
	where = str(Path(path).resolve())
	for root in _vendored_roots():
		if where == root or where.startswith(root + os.sep):
			rest = where[len(root) + 1 :] or "."
			return not any(rest == one or rest.startswith(one) for one in OURS_IN_VENDORED)
	return False


@functools.cache
def _vendored_roots() -> tuple[str, ...]:
	return tuple(str(root.resolve()) for root in VENDORED)


def sources() -> list[Path]:
	return [p for p in _walk() if p.suffix in SOURCE_SUFFIXES]


def python() -> list[Path]:
	return [p for p in _walk() if p.suffix == ".py"]


def fixtures() -> list[Path]:
	"""Doctype definitions and the desk records we ship (workspaces, docks…)."""
	return [p for p in _walk() if p.suffix == ".json"]


def modules() -> list[str]:
	return [line for line in (APP / "modules.txt").read_text().splitlines() if line.strip()]


def module_dir(module: str) -> Path:
	return APP / module.lower().replace(" ", "_").replace("-", "_")


@functools.cache
def _walk() -> tuple[Path, ...]:
	return tuple(path for path in sorted(APP.rglob("*")) if path.is_file() and not any(part in SKIP_DIRS for part in path.parts))


def text(path: Path) -> str:
	path = Path(path)
	stat = path.stat()
	return _text(path, stat.st_mtime_ns, stat.st_size)


@functools.cache
def _text(path: Path, _mtime: int, _size: int) -> str:
	return path.read_text(encoding="utf-8")


@functools.cache
def syntax(source: str) -> ast.Module:
	"""The source's tree, shared by every caller: read it, never change it."""
	return ast.parse(source)


@functools.cache
def nodes(source: str) -> tuple[ast.AST, ...]:
	"""Every node of the source's tree, in `ast.walk`'s order."""
	return tuple(ast.walk(syntax(source)))


def parsed(path: Path) -> ast.Module:
	return syntax(text(path))


def walked(path: Path) -> tuple[ast.AST, ...]:
	return nodes(text(path))


def notifications() -> dict[str, dict]:
	"""Every notification file read in its layout, by name, each with the
	module whose folder it is in (onedesk/notifications/)."""
	import importlib.util

	spec = importlib.util.spec_from_file_location("layout", APP / "notifications" / "layout.py")
	layout = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(layout)
	found = {}
	for path in sorted((APP / "notifications").glob("*/*.md")):
		one = layout.read(path.read_text(encoding="utf-8"))
		assert one["name"] not in found, f"{one['name']} is declared twice"
		found[one["name"]] = {**one, "module": path.parent.name, "file": path}
	for folder, path in declared_notifications():
		spec = importlib.util.spec_from_file_location(f"{folder}_notifications", path)
		module = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(module)
		for one in module.TYPES:
			assert one["name"] not in found, f"{one['name']} is declared twice"
			found[one["name"]] = {**one, "module": folder, "file": path}
	return found


def declared_notifications() -> list[tuple[str, Path]]:
	"""(folder, path) of each module on its way to ready that declares its
	notifications in its own notifications.py (docs/READY.md)."""
	import importlib.util

	spec = importlib.util.spec_from_file_location("ready", APP / "one" / "ready.py")
	ready = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(ready)
	found = []
	for one in ready.MODULES.values():
		path = APP / one["folder"] / "notifications.py"
		if path.exists():
			found.append((one["folder"], path))
	return found


def literal(node):
	"""`ast.literal_eval` of a node that may name an app as
	`registry.name("one_doc")`, read as the name the registry gives it."""
	import copy
	import sys

	if str(ROOT) not in sys.path:
		sys.path.insert(0, str(ROOT))
	from onedesk.one import registry

	class Named(ast.NodeTransformer):
		def visit_Call(self, call):
			if ast.unparse(call.func) == "registry.name" and len(call.args) == 1 and isinstance(call.args[0], ast.Constant):
				return ast.copy_location(ast.Constant(registry.name(call.args[0].value)), call)
			return self.generic_visit(call)

	return ast.literal_eval(Named().visit(copy.deepcopy(node)))


def granted() -> dict:
	"""What one/access.py gives the workspace administrator, by doctype."""
	for node in parsed(APP / "one" / "access.py").body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "ADMINISTRATOR":
			return ast.literal_eval(node.value)
	raise AssertionError("one/access.py has no ADMINISTRATOR")


def suite() -> str:
	"""The integration suite's source: one_demo/check.py, what its checks
	share (checking.py) and each module's own checks.py, which it imports
	(docs/READY.md, A module's folder)."""
	return "\n".join(path.read_text(encoding="utf-8") for path in [APP / "one_demo" / "check.py", APP / "one_demo" / "checking.py", *sorted(APP.glob("*/checks.py"))])


def hooks() -> str:
	"""hooks.py as frappe sees it: each list it builds from the registry
	written out in place of the call that builds it, so a guard reading
	hooks.py finds what the registry gives it where it always was."""
	import sys

	sys.path.insert(0, str(ROOT))
	from onedesk.one.registry import hooks as built

	lists = {f'{name} = hook("{name}")': (name, built.hook(name)) for name in built.derived()}
	lists["after_sync = settles(install=True)"] = ("after_sync", built.settles(install=True))
	lists["after_migrate = settles(install=False)"] = ("after_migrate", built.settles(install=False))
	said = (APP / "hooks.py").read_text(encoding="utf-8")
	for call, name, mapping in (("heirs()", "one_module_heirs", built.heirs()), ("makers()", "one_makes_records", built.makers())):
		rows = "".join(f'\t"{key}": [' + ", ".join(f'"{one}"' for one in value) + "],\n" for key, value in mapping.items())
		said = said.replace(f"{name} = {call}", f"{name} = {{\n{rows}}}")
	for call, (name, entries) in lists.items():
		short = f"{name} = [" + ", ".join(f'"{one}"' for one in entries) + "]"
		long = f"{name} = [\n" + "".join(f'\t"{one}",\n' for one in entries) + "]"
		said = said.replace(call, short if len(short) <= 110 else long)
	return said
