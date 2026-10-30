"""Where the app's own source is, for every tool that walks it."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "onedesk"

SKIP_DIRS = {"__pycache__", "node_modules", "dist", ".git", "locale"}
SOURCE_SUFFIXES = {".py", ".js", ".ts", ".vue", ".css", ".scss"}


#: Code taken whole from another project, held to that project's own rules and
#: refreshed by copying (frontend/src/sheet/VENDORED.md). What we wrote around
#: it, the page and the shims, is ours and checked like the rest.
VENDORED = (ROOT / "frontend" / "src" / "sheet", ROOT / "frontend" / "src" / "writer", ROOT / "frontend" / "src" / "slide")
OURS_IN_VENDORED = ("WorkbookPage.vue", "DocumentPage.vue", "PresentationPage.vue", "seams.mjs", "shim/")


def vendored(path: Path) -> bool:
	for root in VENDORED:
		try:
			rest = str(Path(path).resolve().relative_to(root.resolve()))
		except ValueError:
			continue
		return not any(rest == one or rest.startswith(one) for one in OURS_IN_VENDORED)
	return False


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


def _walk():
	for path in sorted(APP.rglob("*")):
		if not path.is_file() or any(part in SKIP_DIRS for part in path.parts):
			continue
		yield path


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


def granted() -> dict:
	"""What one/access.py gives the workspace administrator, by doctype."""
	import ast

	for node in ast.parse((APP / "one" / "access.py").read_text()).body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "ADMINISTRATOR":
			return ast.literal_eval(node.value)
	raise AssertionError("one/access.py has no ADMINISTRATOR")


def suite() -> str:
	"""The integration suite's source: one_demo/check.py and each module's own
	checks.py, which it imports (docs/READY.md, A module's folder)."""
	return "\n".join(path.read_text(encoding="utf-8") for path in [APP / "one_demo" / "check.py", *sorted(APP.glob("*/checks.py"))])
