"""Points 6 and 7: a record on a page of its own (onedesk/one/tiers.py PAGES)
loses nothing its form has, and the workspace's extensions reach it."""

import importlib.util
import json
import re
from pathlib import Path

import pytest

from onedesk.one import tiers

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "onedesk"
RECORD = (APP / "public" / "js" / "record.js").read_text()
FRAPPE = Path("/home/frappe/bench1/apps/frappe/frappe/public/js/frappe")

ISLANDS = {
	"Project": ROOT / "frontend" / "src" / "project" / "ProjectPage.vue",
	"Project Template": ROOT / "frontend" / "src" / "template" / "TemplatePage.vue",
	"Item": ROOT / "frontend" / "src" / "inventory" / "item" / "ItemPage.vue",
}
DESK_PAGES = {
	"Project": APP / "one_project" / "page" / "project_view" / "project_view.js",
	"Project Template": APP / "one_project" / "page" / "project_template_view" / "project_template_view.js",
	"Item": APP / "one_inventory" / "page" / "item_view" / "item_view.js",
}

PAGE_PLACES = {"Project": "oneproject", "Project Template": "oneproject_template", "Item": "oneinventory_item"}

SIDEBAR = (
	"form/sidebar/form_sidebar.js",
	"form/sidebar/assign_to.js",
	"form/sidebar/attachments.js",
	"form/sidebar/share.js",
	"form/sidebar/user_image.js",
	"form/sidebar/form_sidebar_users.js",
	"form/form_viewers.js",
	"ui/tag_editor.js",
)

DIALOGS = (
	"form/sidebar/share.js",
	"views/communication.js",
	"form/linked_with.js",
	"form/reminders.js",
)


def _places():
	spec = importlib.util.spec_from_file_location("studio_places", APP / "one_studio" / "places.py")
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


def test_every_page_is_drawn_by_a_known_island():
	assert set(ISLANDS) == set(tiers.PAGES)


@pytest.mark.parametrize("doctype", sorted(tiers.PAGES))
def test_a_page_keeps_its_forms_menu_and_sidebar(doctype):
	"""frappe's own form sidebar on the page's right (assigned, attachments,
	tags, shared, likes, viewers, made and changed by), drawn by desk and not
	by the page, and frappe's own menu items under the page's own
	(docs/PASSOVER.md, A record's page)."""
	source = ISLANDS[doctype].read_text()
	assert f'record: "{doctype}"' in DESK_PAGES[doctype].read_text(), "the desk page names its record, for frappe's sidebar"
	assert "onedesk.record_files.side(frm, open_files)" in RECORD
	assert f'useRecord("{doctype}"' in source
	assert "record.menu(" in source
	assert "follow(" in source, "the page hears the record saved, as a form does"
	drawn = [one for one in ("Assigned To", "Shared With", "Currently Viewing", "Last Edited By") if one in source]
	assert len(drawn) < 2, f"the page draws its own {', '.join(drawn)}; frappe's sidebar has them"
	for word in (
		"Print",
		"Email",
		"Show Links",
		"Duplicate",
		"Rename",
		"Delete",
		"Remind Me",
		"Copy to Clipboard",
	):
		assert f'__("{word}")' in RECORD, word
	assert "!!action.standard" in (APP / "public" / "js" / "island_page.js").read_text()


def test_the_record_handle_covers_what_frappes_dialogs_read():
	"""frappe's Share, Email, Links and Remind Me read a form; the handle
	record.js lends them must have every part of one they touch."""
	if not FRAPPE.exists():
		pytest.skip("frappe's source is not beside this checkout")
	handle = RECORD[RECORD.index("onedesk.record.handle =") : RECORD.index("onedesk.record.said =")]
	given = set(re.findall(r"^\t\t(\w+)[,:]", handle, re.M))
	read = set()
	for path in DIALOGS:
		read |= set(re.findall(r"\b(?:this|me)\.frm\??\.(\w+)", (FRAPPE / path).read_text()))
		read |= set(re.findall(r"\bfrm\??\.(\w+)", (FRAPPE / path).read_text()))
	unused = {"share_doc"}
	assert read - given - unused == set(), sorted(read - given - unused)


def test_the_sidebar_stand_in_covers_what_frappes_sidebar_reads():
	"""frappe's form sidebar and its parts read a form; the stand-in
	onedesk.record.sidebar lends them must have every part of one they touch,
	or they make themselves (assign_to, attachments, shared, tags, sidebar,
	viewers)."""
	if not FRAPPE.exists():
		pytest.skip("frappe's source is not beside this checkout")
	handle = RECORD[RECORD.index("onedesk.record.handle =") : RECORD.index("onedesk.record.said =")]
	stand_in = RECORD[RECORD.index("onedesk.record.sidebar =") :]
	given = set(re.findall(r"^\t\t(\w+)[,:]", handle, re.M)) | set(re.findall(r"^\t\t\t(\w+)[,:]", stand_in, re.M))
	made = {"assign_to", "attachments", "shared", "tags", "sidebar", "viewers"}
	read = set()
	for path in SIDEBAR:
		read |= set(re.findall(r"\bfrm\??\.(\w+)", (FRAPPE / path).read_text()))
	assert read - given - made == set(), sorted(read - given - made)
	assert "new frappe.ui.form.Sidebar(" in stand_in and "new frappe.ui.form.FormViewers(" in stand_in


@pytest.mark.parametrize("doctype", sorted(tiers.PAGES))
def test_a_page_declares_its_places_and_fires_them(doctype):
	"""A Client Script reaches a form and a list, not a page of One's: the
	page says what an extension may hear on it, and fires it."""
	places = _places()
	source = "".join(one.read_text() for one in sorted(ISLANDS[doctype].parent.glob("*.vue")))
	place = PAGE_PLACES[doctype]
	assert places.PLACES.get(place, {}).get("record") == doctype, f"no place for {doctype}'s page in one_studio/places.py"
	for place in [place]:
		for event in places.PLACES[place]["events"]:
			assert f'"{place}.{event}"' in source
	assert '"record_head.drawn"' in source


def test_each_page_fires_its_events_with_only_its_powers():
	"""What places.py lists is what the pages fire, and nothing else."""
	places = _places()
	public = APP / "public" / "js"
	fired = {
		"onemail.conversation": (ROOT / "frontend" / "src" / "mail" / "MailConversation.vue").read_text(),
		"onemail.compose": (public / "one_mail" / "mail_compose.js").read_text(),
		"record_head.drawn": (public / "head.js").read_text(),
		"onecalendar.event": (APP / "one_calendar" / "page" / "onecalendar" / "onecalendar.js").read_text(),
		"onecloud.file": (ROOT / "frontend" / "src" / "cloud" / "CloudPreview.vue").read_text(),
		"intake.reading": (ROOT / "frontend" / "src" / "intake" / "IntakeReading.vue").read_text(),
		"onecrm.board": (public / "opportunity_list.js").read_text(),
		"space.home": (public / "places.js").read_text(),
		"oneproject.project": (ROOT / "frontend" / "src" / "project" / "ProjectPage.vue").read_text(),
		**{
			f"oneproject.{view}": (ROOT / "frontend" / "src" / "project" / f"{name}.vue").read_text()
			for view, name in (
				("overview", "Overview"),
				("tasks", "ProjectPage"),
				("time", "Time"),
				("money", "Money"),
				("invoices", "Invoices"),
				("suppliers", "Suppliers"),
				("team", "Team"),
				("files", "Files"),
				("activity", "ProjectActivity"),
			)
		},
		"oneproject_template.template": (ROOT / "frontend" / "src" / "template" / "TemplatePage.vue").read_text(),
		**{
			f"oneinventory_item.{view}": (ROOT / "frontend" / "src" / "inventory" / "item" / f"{name}.vue").read_text()
			for view, name in (
				("item", "ItemPage"),
				("stock", "ItemStock"),
				("buying", "ItemBuying"),
				("selling", "ItemSelling"),
				("making", "ItemMaking"),
				("files", "ItemFiles"),
				("activity", "ItemPage"),
			)
		},
		"oneinventory_stock.on_hand": (ROOT / "frontend" / "src" / "inventory" / "stock" / "StockOnHand.vue").read_text(),
		"oneinventory_floor.shown": (ROOT / "frontend" / "src" / "inventory" / "floor" / "ShopFloor.vue").read_text(),
		"oneinventory_home.shown": (ROOT / "frontend" / "src" / "inventory" / "home" / "InventoryHome.vue").read_text(),
		"onecrm_home.shown": (ROOT / "frontend" / "src" / "crm" / "CrmHome.vue").read_text(),
		"onehr_home.shown": (ROOT / "frontend" / "src" / "hr" / "HrHome.vue").read_text(),
		"onebook_home.shown": (ROOT / "frontend" / "src" / "books" / "BooksHome.vue").read_text(),
		"oneinventory_lots.shown": (ROOT / "frontend" / "src" / "inventory" / "lots" / "LotsPage.vue").read_text(),
		"oneinventory_order.shown": (ROOT / "frontend" / "src" / "inventory" / "to_order" / "ToOrderPage.vue").read_text(),
		"oneinventory_quotes.shown": (ROOT / "frontend" / "src" / "inventory" / "quotes" / "QuotesPage.vue").read_text(),
		"oneinventory_sent_out.shown": (ROOT / "frontend" / "src" / "inventory" / "sent_out" / "SentOutPage.vue").read_text(),
		"oneinventory_upkeep.shown": (ROOT / "frontend" / "src" / "inventory" / "upkeep" / "UpkeepPage.vue").read_text(),
		"oneinventory_plant.shown": (ROOT / "frontend" / "src" / "inventory" / "plant" / "PlantFloor.vue").read_text(),
		"oneproject_workload.week": (APP / "one_project" / "report" / "workload" / "workload.js").read_text(),
		"oneproject_list.projects": (APP / "public" / "js" / "project_list.js").read_text(),
	}
	assert set(fired) == set(places.keys())
	for key, source in fired.items():
		assert f'"{key}"' in source, key
	runtime = (public / "places.js").read_text()
	assert "JSON.parse(JSON.stringify(data" in runtime, "an extension sees a copy, never the page's own"
	assert "onedesk.places.tripped" in runtime
	assert "/assets/onedesk/js/places.js" in (APP / "hooks.py").read_text()


EDITS = {
	"Project": ("project_actions.js", "ABOUT_GROUPS", "ELSEWHERE"),
	"Project Template": ("project_actions.js", "TEMPLATE_GROUPS", "TEMPLATE_ELSEWHERE"),
	"Item": ("item_actions.js", "GROUPS", "ELSEWHERE"),
}
ERPNEXT = Path("/home/frappe/bench1/apps/erpnext/erpnext")
NO_VALUE = {"Section Break", "Column Break", "Tab Break", "HTML", "Button", "Image", "Fold", "Heading"}


def _named(source, constant):
	"""The fieldnames in a constant of an actions file."""
	found = re.search(rf"onedesk\.\w+\.{constant} = (\[.*?\]);\n", source, re.S)
	assert found, constant
	return set(re.findall(r'"([a-z_]+)"', found.group(1)))


def _typed(doctype):
	"""The fields of a doctype that can be typed in, as frappe draws its form:
	ERPNext's own and ours (every custom/*.json), less those our property
	setters hide or make read-only."""
	snake = doctype.lower().replace(" ", "_")
	fields = {df["fieldname"]: df for df in json.loads(next(ERPNEXT.glob(f"*/doctype/{snake}/{snake}.json")).read_text())["fields"]}
	for path in APP.glob("*/custom/*.json"):
		custom = json.loads(path.read_text())
		for df in custom.get("custom_fields", []):
			if df.get("dt") == doctype:
				fields[df["fieldname"]] = df
		for setter in custom.get("property_setters", []):
			if setter.get("doc_type") == doctype and setter.get("field_name") in fields and setter["property"] in ("hidden", "read_only"):
				fields[setter["field_name"]][setter["property"]] = int(setter["value"])
	return {
		name
		for name, df in fields.items()
		if df.get("fieldtype") not in NO_VALUE and not df.get("hidden") and not df.get("read_only")
	}


@pytest.mark.parametrize("doctype", sorted(tiers.PAGES))
def test_a_page_edits_every_field_of_its_record(doctype):
	"""Point 6: a record on a page of its own is edited there, every field of
	it, so its form is a fallback and never the only way in. A field a
	workspace adds shows under More in the same dialog (`about_fields`)."""
	file, groups, elsewhere = EDITS[doctype]
	source = (APP / "public" / "js" / file).read_text()
	placed = _named(source, groups) | _named(source, elsewhere)
	missing = sorted(_typed(doctype) - placed)
	assert not missing, f"{doctype}: {missing} can only be changed on the form; give each a place on the page"
	assert "onedesk.project.about_fields(" in source
	assert '[__("More"), more]' in (APP / "public" / "js" / "project_actions.js").read_text()
