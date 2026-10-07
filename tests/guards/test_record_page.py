"""Point 5: every record's page and every module's places look and move the
same way (docs/PASSOVER.md, The panel and A record's page).

- A record's views are one row of tabs across the top, as a form's are, that
  scrolls sideways when they do not fit, as a form's does
  (frontend/src/kit/ViewTabs.vue). None run down the side, and none stick to
  the top of the page.
- A record's details are frappe's own form sidebar on the page's right
  (onedesk.record.sidebar), not one drawn by the page.
- Where the panel is not out, the breadcrumb is the menu of the module's
  places, for every module from the panel itself (public/js/panel_menu.js).
  No module draws places of its own in the page head.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "onedesk"
SRC = ROOT / "frontend" / "src"
VUE = sorted(SRC.rglob("*.vue"))
JS = sorted((APP / "public" / "js").glob("*.js")) + sorted(APP.glob("*/page/*/*.js"))


def test_no_tabs_run_down_the_side():
	found = [str(path.relative_to(ROOT)) for path in VUE if re.search(r"<Tabs\b[^>]*\bvertical\b", path.read_text())]
	assert not found, found


def test_no_tab_row_sticks_to_the_top():
	found = []
	for path in VUE:
		text = path.read_text()
		for block in re.findall(r"<div[^>]*\bsticky\b[^>]*>[\s\S]{0,600}?</div>", text):
			if re.search(r"<(Tabs|TabList|ViewTabs)\b", block):
				found.append(str(path.relative_to(ROOT)))
	assert "sticky" not in (SRC / "kit" / "ViewTabs.vue").read_text()
	assert not found, found


def test_a_records_views_are_the_one_tab_row():
	"""A page's tabs are ViewTabs, so every page's row scrolls when its tabs
	do not fit, with the chosen one in view; only the kit draws frappe-ui's
	tab parts for a record's views."""
	found = []
	for path in VUE:
		if path.parent.name == "kit":
			continue
		text = path.read_text()
		if "<TabTrigger" in text and re.search(r"defineProps\(\{[\s\S]*onTitle", text):
			found.append(str(path.relative_to(ROOT)))
	assert not found, found
	assert "<ViewTabs" in (SRC / "project" / "ProjectPage.vue").read_text()
	row = (SRC / "kit" / "ViewTabs.vue").read_text()
	assert "overflow-x-auto" in row and "flex-nowrap" in row, "the row scrolls, as a form's tabs do"
	assert "Dropdown" not in row, "no tab is hidden in a menu"
	assert "function reveal()" in row, "the chosen tab is kept in view"


def test_no_page_draws_its_own_record_sidebar():
	assert not (SRC / "kit" / "Record.vue").exists()
	found = [str(path.relative_to(ROOT)) for path in VUE if re.search(r"__\(['\"](Assigned To|Shared With|Currently Viewing)['\"]", path.read_text())]
	assert not found, found


def test_the_breadcrumb_is_the_panels_menu_everywhere():
	hooks = (APP / "hooks.py").read_text()
	assert '"/assets/onedesk/js/panel_menu.js"' in hooks
	menu = (APP / "public" / "js" / "panel_menu.js").read_text()
	assert ".body-sidebar .sidebar-items .item-anchor" in menu, "the places are the panel's own rows"
	assert "frappe.is_mobile()" in menu and "hide_sidebar" in menu
	# No module puts places of its own beside the breadcrumb.
	found = [str(path.relative_to(ROOT)) for path in JS if "navbar-breadcrumbs" in path.read_text() and path.name != "panel_menu.js"]
	assert not found, found
