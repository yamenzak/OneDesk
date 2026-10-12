"""Point 4: how each doctype is shown is declared (onedesk/one/tiers.py), and
no view frappe offers is taken away."""

import ast
import re
from pathlib import Path

from onedesk.one import tiers

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "onedesk"
HOOKS = (APP / "hooks.py").read_text(encoding="utf-8")


def _hook(name: str) -> dict:
	tree = ast.parse((APP / "hooks.py").read_text())
	for node in tree.body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == name:
			return ast.literal_eval(node.value)
	return {}


#: Heads whose doctype is a name in code, and the line that names it.
NAMED_IN_CODE = {
	"Credit Ledger Entry": ("one_admin/heads.py", '"doctype": ledger.ENTRY,'),
	"Extension": ("one_studio/heads.py", '"doctype": extensions.EXTENSION,'),
	"Sales Invoice": ("one_book/paid.py", 'SETTLED = ("Sales Invoice", "Purchase Invoice")'),
	"Purchase Invoice": ("one_book/paid.py", 'SETTLED = ("Sales Invoice", "Purchase Invoice")'),
}


def test_every_record_head_is_declared():
	found, named = set(), 0
	for path in APP.glob("*/heads.py"):
		source = path.read_text()
		if "HEADS = [" in source:
			heads = source.split("HEADS = [", 1)[1]
			found |= set(re.findall(r'\{\n\t\t"doctype": "([^"]+)"', heads))
			named += len(re.findall(r'\{\n\t\t"doctype": [a-z_.]+,', heads, re.I))
	for doctype, (file, line) in NAMED_IN_CODE.items():
		assert line in (APP / file).read_text(), doctype
	assert named == 3, "a head naming its doctype in code must be added to NAMED_IN_CODE"
	assert found | set(NAMED_IN_CODE) == set(tiers.HEADS), sorted(
		(found | set(NAMED_IN_CODE)) ^ set(tiers.HEADS)
	)


def test_every_page_of_its_own_is_declared():
	# Each island and the record it is the page of; None for a screen of many
	# records (SCREENS).
	islands = {
		"onedesk.project": "Project",
		"onedesk.template": "Project Template",
		"onedesk.task": "Task",
		"onedesk.item": "Item",
		"onedesk.stock": None,
		"onedesk.home": None,
		"onedesk.lots": None,
		"onedesk.quotes": None,
		"onedesk.sent_out": None,
		"onedesk.floor": None,
		"onedesk.plant": None,
		"onedesk.my_tasks": None,
		"onedesk.timers": None,
	}
	build = (APP.parent / "frontend" / "build-islands.mjs").read_text()
	assert set(re.findall(r'"(onedesk\.\w+)":', build)) == set(islands)
	assert {one for one in islands.values() if one} == set(tiers.PAGES)
	assert all(reason for reason in [*tiers.PAGES.values(), *tiers.NEXT_PAGES.values()])


def test_every_collection_set_up_is_declared():
	for hook, view in (
		("doctype_list_js", "List"),
		("doctype_calendar_js", "Calendar"),
		("doctype_tree_js", "Tree"),
	):
		for doctype in _hook(hook):
			assert view in tiers.COLLECTIONS.get(doctype, {}), (hook, doctype)
	for doctype, views in tiers.COLLECTIONS.items():
		assert set(views) <= set(tiers.VIEWS), doctype


#: frappe's view classes, and the view each draws.
VIEW_CLASSES = {
	"ReportView": "Report",
	"DashboardView": "Dashboard",
	"GanttView": "Gantt",
	"KanbanV2Page": "Kanban",
	"TreeView": "Tree",
	"CalendarView": "Calendar",
	"ImageView": "Image",
	"MapView": "Map",
	"InboxView": "Inbox",
}


def test_every_view_we_change_for_a_doctype_is_declared():
	"""A file that changes one of frappe's views for a doctype (`this.doctype
	=== "Project"`) declares that view for it, as the hooks' views are."""
	for path in (APP / "public" / "js").rglob("*.js"):
		source = path.read_text()
		doctypes = set(re.findall(r'this\.doctype\s*[!=]==\s*"([^"]+)"', source))
		for cls, view in VIEW_CLASSES.items():
			if f"frappe.views.{cls}" not in source:
				continue
			for doctype in doctypes:
				assert view in tiers.COLLECTIONS.get(doctype, {}), (path.name, doctype, view)


def test_no_view_frappe_offers_is_taken_away():
	for path in (APP / "public" / "js").rglob("*.js"):
		source = path.read_text()
		assert "delete found." not in source, path.name
		assert not re.search(r"get_views\s*=\s*function[^}]*delete ", source, re.S), path.name


def test_every_desk_page_of_ours_is_declared():
	pages = {path.parent.name.replace("_", "-") for path in APP.glob("*/page/*/*.json")}
	assert pages == set(tiers.SCREENS), sorted(pages ^ set(tiers.SCREENS))


def test_a_record_tab_is_declared_by_its_module_and_drawn_in_one_place():
	"""Stage 8: Mail, Files and Activity are rows under one_record_tabs, and
	record_tabs.js is the only script that adds to a form's layout for them."""
	js = APP / "public" / "js"
	patched = [
		path.name
		for path in js.glob("*.js")
		if "Layout.prototype.get_doctype_fields" in path.read_text(encoding="utf-8")
	]
	assert sorted(patched) == ["head.js", "record_tabs.js"], patched
	hooks = HOOKS.split("one_record_tabs = [", 1)[1].split("]", 1)[0]
	for declared in ("one_mail.linking.TABS", "one_storage.namespace.TABS", "one.tabs.TABS"):
		assert declared in hooks, declared
	for name, script in (
		("mail", "record_mail.js"),
		("files", "record_files.js"),
		("activity", "record_activity.js"),
	):
		assert f'onedesk.record_tabs.register("{name}"' in (js / script).read_text(encoding="utf-8"), name
	assert HOOKS.index("record_tabs.js") < HOOKS.index("record_files.js")


def test_every_number_card_names_the_record_type_it_counts():
	"""frappe shows a Custom number card only to somebody who may read its
	record type, so one that names none is shown to nobody but the system
	manager: One's own home was empty for everybody."""
	import json

	blind = [
		path.parent.name
		for path in APP.glob("*/number_card/*/*.json")
		if json.loads(path.read_text()).get("type") in ("Custom", "Document Type")
		and not json.loads(path.read_text()).get("document_type")
	]
	assert not blind, blind
