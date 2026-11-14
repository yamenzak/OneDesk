"""Point 4: how each doctype is shown is declared (onedesk/one/tiers.py), and
no view frappe offers is taken away."""

import ast
import re
from pathlib import Path

from onedesk.one import tiers
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import tree  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "onedesk"
HOOKS = tree.hooks()


def _hook(name: str) -> dict:
	parsed = ast.parse(tree.hooks())
	for node in parsed.body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == name:
			return ast.literal_eval(node.value)
	return {}


NAMED_IN_CODE = {
	"Credit Ledger Entry": ("one_admin/heads.py", '"doctype": ledger.ENTRY,'),
	"Extension": ("one_studio/heads.py", '"doctype": extensions.EXTENSION,'),
	"Sales Invoice": ("one_book/paid.py", 'SETTLED = ("Sales Invoice", "Purchase Invoice")'),
	"Purchase Invoice": ("one_book/paid.py", 'SETTLED = ("Sales Invoice", "Purchase Invoice")'),
}


def heads_in(source: str) -> tuple[set[str], int]:
	"""The doctypes a heads.py's HEADS names by string, and how many it names
	in code. Pure."""
	if "HEADS = [" not in source:
		return set(), 0
	heads = source.split("HEADS = [", 1)[1]
	return set(re.findall(r'\{\n\t\t"doctype": "([^"]+)"', heads)), len(re.findall(r'\{\n\t\t"doctype": [a-z_.]+,', heads, re.I))


def test_every_record_head_is_declared():
	found, named = set(), 0
	for path in APP.glob("*/heads.py"):
		strings, coded = heads_in(path.read_text())
		found |= strings
		named += coded
	for doctype, (file, line) in NAMED_IN_CODE.items():
		assert line in (APP / file).read_text(), doctype
	assert named == 3, "a head naming its doctype in code must be added to NAMED_IN_CODE"
	assert found | set(NAMED_IN_CODE) == set(tiers.HEADS), sorted(
		(found | set(NAMED_IN_CODE)) ^ set(tiers.HEADS)
	)


def test_every_page_of_its_own_is_declared():
	islands = {
		"onedesk.project_part": None,
		"onedesk.template_part": None,
		"onedesk.stock": None,
		"onedesk.one_home": None,
		"onedesk.hub": None,
		"onedesk.marketplace": None,
		"onedesk.home": None,
		"onedesk.books": None,
		"onedesk.crm": None,
		"onedesk.hr": None,
		"onedesk.to_order": None,
		"onedesk.supplier_items": None,
		"onedesk.item_part": None,
		"onedesk.check": None,
		"onedesk.workload": None,
		"onedesk.floor": None,
		"onedesk.factory": None,
		"onedesk.quality": None,
		"onedesk.timers": None,
		"onedesk.counter": None,
		"onedesk.boards": None,
		"onedesk.workbook": None,
		"onedesk.document": None,
		"onedesk.presentation": None,
		"onedesk.onemail": None,
		"onedesk.onecloud": None,
		"onedesk.onechat": None,
		"onedesk.automation": None,
		"onedesk.oneadmin": None,
		"onedesk.oneadmin_servers": None,
		"onedesk.oneadmin_server_part": None,
		"onedesk.oneadmin_billing": None,
		"onedesk.oneadmin_releases": None,
		"onedesk.oneadmin_status": None,
		"onedesk.oneadmin_sessions": None,
		"onedesk.head": None,
	}
	build = (APP.parent / "frontend" / "build-islands.mjs").read_text()
	found = pages_undeclared(build, islands, tiers.PAGES, tiers.NEXT_PAGES)
	assert not found, found


def pages_undeclared(build: str, islands: dict, pages: dict, next_pages: dict) -> list[str]:
	"""An island built and not listed, a page of its own not declared, or one
	declared without why. Pure."""
	out = []
	built = set(re.findall(r'"(onedesk\.\w+)":', build))
	if built != set(islands):
		out.append(f"built and listed differ: {sorted(built ^ set(islands))}")
	if {one for one in islands.values() if one} != set(pages):
		out.append("pages of their own differ from tiers.PAGES")
	return out + [name for name, reason in [*pages.items(), *next_pages.items()] if not reason]


COLLECTION_HOOKS = (("doctype_list_js", "List"), ("doctype_calendar_js", "Calendar"), ("doctype_tree_js", "Tree"))


def collections_undeclared(hooks: dict[str, dict], collections: dict, views) -> list:
	"""A doctype a collection hook sets up whose view is not declared, or a
	declared view frappe has not. Pure."""
	out = [(hook, doctype) for hook, view in COLLECTION_HOOKS for doctype in hooks.get(hook, {}) if view not in collections.get(doctype, {})]
	return out + [doctype for doctype, declared in collections.items() if not set(declared) <= set(views)]


def test_every_collection_set_up_is_declared():
	found = collections_undeclared({hook: _hook(hook) for hook, _view in COLLECTION_HOOKS}, tiers.COLLECTIONS, tiers.VIEWS)
	assert not found, found


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
		found = views_undeclared(path.read_text(), tiers.COLLECTIONS)
		assert not found, (path.name, found)


def views_undeclared(source: str, collections: dict) -> list[tuple[str, str]]:
	"""The (doctype, view) a script changes and the collections do not
	declare. Pure."""
	doctypes = set(re.findall(r'this\.doctype\s*[!=]==\s*"([^"]+)"', source))
	return [
		(doctype, view)
		for cls, view in VIEW_CLASSES.items()
		if f"frappe.views.{cls}" in source
		for doctype in sorted(doctypes)
		if view not in collections.get(doctype, {})
	]


def takes_a_view_away(source: str) -> bool:
	"""Whether a script deletes a view frappe offers. Pure."""
	return "delete found." in source or bool(re.search(r"get_views\s*=\s*function[^}]*delete ", source, re.S))


def test_no_view_frappe_offers_is_taken_away():
	for path in (APP / "public" / "js").rglob("*.js"):
		assert not takes_a_view_away(path.read_text()), path.name


def screens_undeclared(folders, screens) -> list[str]:
	"""The page folders with no screen declared, and the screens with no
	page. Pure."""
	return sorted({folder.replace("_", "-") for folder in folders} ^ set(screens))


def test_every_desk_page_of_ours_is_declared():
	found = screens_undeclared([path.parent.name for path in APP.glob("*/page/*/*.json")], tiers.SCREENS)
	assert not found, found


def test_a_record_tab_is_declared_by_its_module_and_drawn_in_one_place():
	"""Stage 8: Mail, Files and Activity are rows under one_record_tabs, and
	record_tabs.js is the only script that adds to a form's layout for them."""
	js = APP / "public" / "js"
	scripts = {path.name: path.read_text(encoding="utf-8") for path in [*js.glob("*.js"), *js.glob("*/*.js")]}
	tabs = {script: (js / script).read_text(encoding="utf-8") for _name, script in RECORD_TABS}
	found = record_tab_problems(scripts, tabs, HOOKS)
	assert not found, found


RECORD_TABS = (("mail", "one_mail/record_mail.js"), ("files", "one_cloud/record_files.js"), ("activity", "one_cloud/record_activity.js"))


def record_tab_problems(scripts: dict[str, str], tabs: dict[str, str], hooks: str) -> list[str]:
	"""A script besides head.js and record_tabs.js adding to a form's layout,
	a tab row not declared under one_record_tabs, or a tab script not
	registering its tab after record_tabs.js loads. Pure."""
	out = []
	patched = sorted(name for name, source in scripts.items() if "Layout.prototype.get_doctype_fields" in source)
	if patched != ["head.js", "record_tabs.js"]:
		out.append(f"patched: {patched}")
	declared = hooks.split("one_record_tabs = [", 1)[1].split("]", 1)[0] if "one_record_tabs = [" in hooks else ""
	out += [one for one in ("one_mail.linking.TABS", "one_cloud.namespace.TABS", "one.tabs.TABS") if one not in declared]
	out += [name for name, script in RECORD_TABS if f'onedesk.record_tabs.register("{name}"' not in tabs.get(script, "")]
	if "record_tabs.js" not in hooks or "record_files.js" not in hooks or hooks.index("record_tabs.js") > hooks.index("record_files.js"):
		out.append("record_tabs.js is not loaded before record_files.js")
	return out


def test_every_number_card_names_the_record_type_it_counts():
	"""frappe shows a Custom number card only to somebody who may read its
	record type, so one that names none is shown to nobody but the system
	manager: One's own home was empty for everybody."""
	import json

	found = blind({path.parent.name: json.loads(path.read_text()) for path in APP.glob("*/number_card/*/*.json")})
	assert not found, found


def blind(cards: dict[str, dict]) -> list[str]:
	"""The number cards frappe shows to nobody: a counting one naming no
	record type. Pure."""
	return [name for name, card in cards.items() if card.get("type") in ("Custom", "Document Type") and not card.get("document_type")]


def test_the_tier_rules_catch_their_examples():
	assert heads_in('HEADS = [\n\t{\n\t\t"doctype": "Item",\n\t},\n\t{\n\t\t"doctype": ledger.ENTRY,\n') == ({"Item"}, 1)
	assert pages_undeclared('"onedesk.stock": x', {"onedesk.stock": None}, {}, {}) == []
	assert pages_undeclared('"onedesk.stock": x, "onedesk.new": y', {"onedesk.stock": None}, {}, {"Floor": ""})
	assert collections_undeclared({"doctype_list_js": {"Item": "x.js"}}, {}, tiers.VIEWS) == [("doctype_list_js", "Item")]
	assert collections_undeclared({"doctype_list_js": {"Item": "x.js"}}, {"Item": {"List": ""}}, {"List"}) == []
	assert collections_undeclared({}, {"Item": {"Nowhere": ""}}, {"List"}) == ["Item"]
	changes = 'frappe.views.GanttView = class extends frappe.views.GanttView { x() { if (this.doctype === "Task") {} } }'
	assert views_undeclared(changes, {}) == [("Task", "Gantt")]
	assert views_undeclared(changes, {"Task": {"Gantt": ""}}) == []
	assert takes_a_view_away("frappe.get_views = function () { delete views.Kanban; }")
	assert takes_a_view_away("delete found.Report;") and not takes_a_view_away("frappe.get_views = function () { return v; }")
	assert screens_undeclared(["stock_floor"], ["stock-floor"]) == [] and screens_undeclared(["new_page"], []) == ["new-page"]
	good = {"head.js": "Layout.prototype.get_doctype_fields", "record_tabs.js": "Layout.prototype.get_doctype_fields"}
	tabs = {script: f'onedesk.record_tabs.register("{name}"' for name, script in RECORD_TABS}
	hooks = 'one_record_tabs = ["one_mail.linking.TABS", "one_cloud.namespace.TABS", "one.tabs.TABS"]\nx = ["record_tabs.js", "record_files.js"]'
	assert record_tab_problems(good, tabs, hooks) == []
	assert record_tab_problems({**good, "mine.js": "Layout.prototype.get_doctype_fields"}, tabs, hooks)
	assert record_tab_problems(good, {}, hooks) == ["mail", "files", "activity"]
	assert blind({"open": {"type": "Custom"}, "seen": {"type": "Custom", "document_type": "Task"}}) == ["open"]
