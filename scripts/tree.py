"""Where the app's own source is, for every tool that walks it."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "onedesk"

SKIP_DIRS = {"__pycache__", "node_modules", "dist", ".git", "locale"}
SOURCE_SUFFIXES = {".py", ".js", ".ts", ".vue", ".css", ".scss"}


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
	return found
