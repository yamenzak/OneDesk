"""Desk furniture is fixture JSON, synced by migrate — never built at runtime.

A workspace assembled in Python is a workspace nobody can find by looking, and
one `bench migrate` away from disagreeing with itself.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

DECLARED = (
	"Workspace",
	"Dock",
	"Custom Sidebar",
	"Sidebar",
	"Role",
	"Custom Field",
	"Property Setter",
	"Notification",
	"Print Format",
	"Workflow",
)

_OPENS = r"frappe\.(get_doc|new_doc|_dict)\s*\(\s*[{'\"]?[^)]*?['\"]("
_CLOSES = r")['\"]"


def _pattern() -> re.Pattern:
	return re.compile(_OPENS + "|".join(re.escape(d) for d in DECLARED) + _CLOSES)


def test_desk_furniture_is_not_built_in_python():
	pattern = _pattern()
	hits = [
		f"{path.relative_to(tree.ROOT)}:{n}: {line.strip()}"
		for path in tree.python()
		for n, line in enumerate(path.read_text().splitlines(), 1)
		if not line.lstrip().startswith("#") and pattern.search(line)
	]
	assert not hits, (
		"these belong in the app as fixture JSON, not in code:\n" + "\n".join(hits)
	)


def test_the_scan_would_catch_one():
	pattern = _pattern()
	assert pattern.search('frappe.get_doc({"doctype": "Workspace", "label": "One"})')
	assert not pattern.search('frappe.get_doc("Task", name)')


#: The icon grid, which `frappe/desk/RETIRING.md` lists for removal in one batch.
#: Navigation here is the Apps screen: `add_to_apps_screen`, a `Dock`, a `Sidebar`.
RETIRING = ("Desktop Icon", "Desktop Layout", "Workspace Sidebar")


def test_we_ship_nothing_for_the_retiring_navigation():
	hits = [
		str(path.relative_to(tree.ROOT))
		for path in tree.fixtures()
		if _doctype_of(path) in RETIRING
	]
	assert not hits, (
		"the icon grid is on frappe's removal list — put it in the dock instead:\n"
		+ "\n".join(hits)
	)


def _doctype_of(path: Path) -> str:
	import json

	try:
		return json.loads(path.read_text()).get("doctype", "")
	except (ValueError, UnicodeDecodeError):
		return ""


def test_every_module_in_modules_txt_has_a_folder():
	missing = [m for m in tree.modules() if not tree.module_dir(m).is_dir()]
	assert not missing, f"named in modules.txt with no folder: {missing}"


def test_every_module_folder_is_in_modules_txt():
	known = {tree.module_dir(m).name for m in tree.modules()}
	strays = [
		p.name
		for p in tree.APP.iterdir()
		if p.is_dir()
		and (p / "__init__.py").exists()
		and p.name not in known
		and p.name not in {"public", "patches", "config", "templates", "www"}
	]
	assert not strays, f"module folders missing from modules.txt: {strays}"
