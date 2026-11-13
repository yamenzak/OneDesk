"""Point 7: every record's page and every module's places look and move the
same way (docs/STANDARD.md, The panel and A record's page).

- A record's views are one row of tabs across the top, as a form's are, that
  scrolls sideways when they do not fit, as a form's does
  (frontend/src/kit/ViewTabs.vue). None run down the side, and none stick to
  the top of the page.
- A record's details are frappe's own form sidebar on the page's right
  (onedesk.record.sidebar), not one drawn by the page.
- Every crumb with somewhere to go is a searchable switcher
  (public/js/crumb_switch.js): the place's lists the module's places from
  the panel itself, the record's searches its kind as a link field does.
  No module draws places of its own in the page head, and no crumb is a
  menu of its own.
- On a phone the head is two bars and the trail splits over them: the place
  and the page's buttons in the first, the record in the second
  (public/js/phone_head.js, desk.css).
"""

import re
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import tree  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "onedesk"
SRC = ROOT / "frontend" / "src"
VUE = sorted(SRC.rglob("*.vue"))
JS = sorted((APP / "public" / "js").glob("*.js")) + sorted((APP / "public" / "js").glob("one_*/*.js")) + sorted(APP.glob("*/page/*/*.js"))


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
	assert "<ViewTabs" in (SRC / "inventory" / "home" / "InventoryHome.vue").read_text()
	row = (SRC / "kit" / "ViewTabs.vue").read_text()
	assert "overflow-x-auto" in row and "flex-nowrap" in row, "the row scrolls, as a form's tabs do"
	assert "Dropdown" not in row, "no tab is hidden in a menu"
	assert "function reveal()" in row, "the chosen tab is kept in view"


def test_no_page_draws_its_own_record_sidebar():
	assert not (SRC / "kit" / "Record.vue").exists()
	found = [
		str(path.relative_to(ROOT))
		for path in VUE
		if len(set(re.findall(r"__\(['\"](Assigned To|Shared With|Currently Viewing)['\"]", path.read_text()))) > 1
	]
	assert not found, found


def test_every_crumb_is_a_searchable_switcher():
	hooks = tree.hooks()
	assert '"/assets/onedesk/js/panel_menu.js"' in hooks and '"/assets/onedesk/js/crumb_switch.js"' in hooks
	panel = (APP / "public" / "js" / "panel_menu.js").read_text()
	assert ".body-sidebar .sidebar-items .item-anchor" in panel, "the places are the panel's own rows"
	switch = (APP / "public" / "js" / "crumb_switch.js").read_text()
	assert "new frappe.ui.Popover({" in switch and 'type="text"' in switch, "a crumb opens a search over its choices"
	assert "frappe.desk.search.search_link" in switch, "a record's crumb searches its kind as a link field does"
	assert "onedesk.crumbs.places(" in switch and "onedesk.crumbs.records(" in switch
	found = [
		str(path.relative_to(ROOT))
		for path in JS
		if ("navbar-breadcrumbs" in path.read_text() or "new frappe.ui.Dropdown({ trigger: $crumb" in path.read_text())
		and path.name != "crumb_switch.js"
	]
	assert not found, found


def test_a_phone_head_is_two_rows():
	hooks = tree.hooks()
	assert '"/assets/onedesk/js/phone_head.js"' in hooks
	head = (APP / "public" / "js" / "phone_head.js").read_text()
	assert "--page-head-height" in head, "frappe's sticky parts are told the head's height"
	assert "search.before(buttons)" in head, "the page's buttons are in the first bar"
	css = (APP / "public" / "css" / "desk.css").read_text()
	phone = css[css.index("@media (max-width: 767.98px)") :]
	assert "flex-wrap: wrap !important" in phone and "flex: 1 0 100%" in phone, "the page's buttons wrap to a row of their own"
	assert "li.one-crumb-switch:not(:last-child)" in phone, "a phone shows every crumb that switches"
	assert "border-top: 1px solid" in phone and "height: 44px" in phone, "the second bar is a bar of its own"
	switch = (APP / "public" / "js" / "crumb_switch.js").read_text()
	assert "one-head-scope" in switch and "one-head-record" in switch, "the record and its scope are in the second bar"
	assert "li.one-crumb-record" in phone, "the first bar keeps the place, not the record"


def test_a_records_activity_is_written_as_a_forms_is():
	"""A record's activity reads as a form's Activity does: the comment box at
	its top (frappe's CommentComposer, kit/ActivityComposer.vue), New Email
	opening frappe's own Email dialog (record.js `onedesk.record.email`, the
	arguments of the form timeline's compose_mail), newest first, and Reply
	and Reply All on each email. No page draws a comment box or sends mail
	of its own."""
	kit = (SRC / "kit" / "ActivityComposer.vue").read_text()
	assert "CommentComposer" in kit and "EmailComposer" not in kit
	assert "emailOn(" in kit and "New Email" in kit
	record = (APP / "public" / "js" / "record.js").read_text()
	assert "onedesk.record.email = " in record and "new frappe.views.CommunicationComposer(args)" in record
	assert "is_a_reply" in record and "reply_all" in record
	found = []
	for path in VUE:
		if path.parent.name == "kit":
			continue
		text = path.read_text()
		if re.search(r"\bcomment\(", text) or "communication.email.make" in text:
			found.append(f"{path.relative_to(ROOT)} sends on its own")
		if "useActivityTimeline(" not in text:
			continue
		if "<ActivityComposer" not in text or "composer?.reply(one)" not in text or "composer?.reply(one, true)" not in text:
			found.append(f"{path.relative_to(ROOT)} lacks the composer or Reply and Reply All")
		if text.index("<ActivityComposer") > text.index("<ActivityTimeline"):
			found.append(f"{path.relative_to(ROOT)} has its comment box under the timeline")
		if "<TimelineContainer" in text:
			found.append(f"{path.relative_to(ROOT)} lists oldest first")
	assert not found, found


def test_an_island_is_inside_frappe_uis_provider():
	"""Every island mounts inside FrappeUIProvider, as a Frappe UI app's root
	does, so frappe-ui's toasts and dialogs show; and frappe-ui reads frappe's
	times in the site's timezone."""
	mount = (SRC / "kit" / "mount.js").read_text()
	assert "h(FrappeUIProvider" in mount
	assert 'setConfig("systemTimezone"' in mount
	desk = (SRC / "kit" / "desk.js").read_text()
	code = "\n".join(line for line in desk.splitlines() if not line.lstrip().startswith(("//", "*", "/*")))
	assert not re.search(r"(?<![\w.\"'`])frappe\.\w", code.replace("window.frappe", "")), "call frappe() in the kit"
