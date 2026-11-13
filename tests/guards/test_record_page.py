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
JS = sorted((APP / "public" / "js").glob("*.js")) + sorted((APP / "public" / "js").glob("*/*.js")) + sorted(APP.glob("*/page/*/*.js"))



def tabs_down_the_side(text: str) -> bool:
	"""Whether a screen's tabs run down the side. Pure."""
	return bool(re.search(r"<Tabs\b[^>]*\bvertical\b", text))


def test_no_tabs_run_down_the_side():
	found = [str(path.relative_to(ROOT)) for path in VUE if tabs_down_the_side(path.read_text())]
	assert not found, found


def tabs_stick(text: str) -> bool:
	"""Whether a screen puts a tab row in a sticky block. Pure."""
	return any(re.search(r"<(Tabs|TabList|ViewTabs)\b", block) for block in re.findall(r"<div[^>]*\bsticky\b[^>]*>[\s\S]{0,600}?</div>", text))


def test_no_tab_row_sticks_to_the_top():
	found = [str(path.relative_to(ROOT)) for path in VUE if tabs_stick(path.read_text())]
	assert "sticky" not in (SRC / "kit" / "ViewTabs.vue").read_text()
	assert not found, found


def own_view_tabs(text: str) -> bool:
	"""Whether a screen outside the kit draws frappe-ui's tab parts for a
	record's views. Pure."""
	return "<TabTrigger" in text and bool(re.search(r"defineProps\(\{[\s\S]*onTitle", text))


def view_row_lacks(row: str) -> list[str]:
	"""What the kit's ViewTabs lacks of a form's tab row. Pure."""
	out = [] if "overflow-x-auto" in row and "flex-nowrap" in row else ["the row scrolls, as a form's tabs do"]
	if "Dropdown" in row:
		out.append("no tab is hidden in a menu")
	return out + ([] if "function reveal()" in row else ["the chosen tab is kept in view"])


def test_a_records_views_are_the_one_tab_row():
	"""A page's tabs are ViewTabs, so every page's row scrolls when its tabs
	do not fit, with the chosen one in view; only the kit draws frappe-ui's
	tab parts for a record's views."""
	found = [str(path.relative_to(ROOT)) for path in VUE if path.parent.name != "kit" and own_view_tabs(path.read_text())]
	assert not found, found
	assert "<ViewTabs" in (SRC / "inventory" / "home" / "InventoryHome.vue").read_text()
	found = view_row_lacks((SRC / "kit" / "ViewTabs.vue").read_text())
	assert not found, found


def own_record_sidebar(text: str) -> bool:
	"""Whether a screen draws more than one part of frappe's form sidebar. Pure."""
	return len(set(re.findall(r"__\(['\"](Assigned To|Shared With|Currently Viewing)['\"]", text))) > 1


def test_no_page_draws_its_own_record_sidebar():
	assert not (SRC / "kit" / "Record.vue").exists()
	found = [str(path.relative_to(ROOT)) for path in VUE if own_record_sidebar(path.read_text())]
	assert not found, found


def switcher_lacks(hooks: str, panel: str, switch: str) -> list[str]:
	"""What the crumbs' switcher lacks: loaded, the panel's own rows, a
	search over its choices, a link field's search, places and records. Pure."""
	out = [] if '"/assets/onedesk/js/panel_menu.js"' in hooks and '"/assets/onedesk/js/crumb_switch.js"' in hooks else ["not loaded"]
	if ".body-sidebar .sidebar-items .item-anchor" not in panel:
		out.append("the places are the panel's own rows")
	if not ("new frappe.ui.Popover({" in switch and 'type="text"' in switch):
		out.append("a crumb opens a search over its choices")
	if "frappe.desk.search.search_link" not in switch:
		out.append("a record's crumb searches its kind as a link field does")
	return out + ([] if "onedesk.crumbs.places(" in switch and "onedesk.crumbs.records(" in switch else ["places and records"])


def crumbs_of_its_own(name: str, text: str) -> bool:
	"""Whether a script other than crumb_switch.js draws crumbs or a crumb's
	menu of its own. Pure."""
	return name != "crumb_switch.js" and ("navbar-breadcrumbs" in text or "new frappe.ui.Dropdown({ trigger: $crumb" in text)


def test_every_crumb_is_a_searchable_switcher():
	panel = (APP / "public" / "js" / "panel_menu.js").read_text()
	switch = (APP / "public" / "js" / "crumb_switch.js").read_text()
	lacks = switcher_lacks(tree.hooks(), panel, switch)
	assert not lacks, lacks
	found = [str(path.relative_to(ROOT)) for path in JS if crumbs_of_its_own(path.name, path.read_text())]
	assert not found, found


def phone_head_lacks(hooks: str, head: str, css: str, switch: str) -> list[str]:
	"""What a phone's head lacks of two bars. Pure."""
	out = [] if '"/assets/onedesk/js/phone_head.js"' in hooks else ["phone_head.js is not loaded"]
	if "--page-head-height" not in head:
		out.append("frappe's sticky parts are told the head's height")
	if "search.before(buttons)" not in head:
		out.append("the page's buttons are in the first bar")
	phone = css[css.index("@media (max-width: 767.98px)") :] if "@media (max-width: 767.98px)" in css else ""
	for needed, said in (
		("flex-wrap: wrap !important" in phone and "flex: 1 0 100%" in phone, "the page's buttons wrap to a row of their own"),
		("li.one-crumb-switch:not(:last-child)" in phone, "a phone shows every crumb that switches"),
		("border-top: 1px solid" in phone and "height: 44px" in phone, "the second bar is a bar of its own"),
		("one-head-scope" in switch and "one-head-record" in switch, "the record and its scope are in the second bar"),
		("li.one-crumb-record" in phone, "the first bar keeps the place, not the record"),
	):
		if not needed:
			out.append(said)
	return out


def test_a_phone_head_is_two_rows():
	head = (APP / "public" / "js" / "phone_head.js").read_text()
	css = (APP / "public" / "css" / "desk.css").read_text()
	switch = (APP / "public" / "js" / "crumb_switch.js").read_text()
	found = phone_head_lacks(tree.hooks(), head, css, switch)
	assert not found, found


def activity_unlike_a_forms(text: str) -> list[str]:
	"""How a screen outside the kit writes a record's activity unlike a
	form's: sending on its own, without the composer or Reply and Reply All,
	the comment box under the timeline, or oldest first. Pure."""
	out = ["sends on its own"] if re.search(r"\bcomment\(", text) or "communication.email.make" in text else []
	if "useActivityTimeline(" not in text:
		return out
	if "<ActivityComposer" not in text or "composer?.reply(one)" not in text or "composer?.reply(one, true)" not in text:
		out.append("lacks the composer or Reply and Reply All")
	if text.index("<ActivityComposer") > text.index("<ActivityTimeline"):
		out.append("has its comment box under the timeline")
	return out + (["lists oldest first"] if "<TimelineContainer" in text else [])


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
	found = [
		f"{path.relative_to(ROOT)} {said}"
		for path in VUE
		if path.parent.name != "kit"
		for said in activity_unlike_a_forms(path.read_text())
	]
	assert not found, found


def kit_calls_frappe(desk: str) -> bool:
	"""Whether the kit's desk.js reaches frappe's globals outside frappe(). Pure."""
	code = "\n".join(line for line in desk.splitlines() if not line.lstrip().startswith(("//", "*", "/*")))
	return bool(re.search(r"(?<![\w.\"'`])frappe\.\w", code.replace("window.frappe", "")))


def test_an_island_is_inside_frappe_uis_provider():
	"""Every island mounts inside FrappeUIProvider, as a Frappe UI app's root
	does, so frappe-ui's toasts and dialogs show; and frappe-ui reads frappe's
	times in the site's timezone."""
	mount = (SRC / "kit" / "mount.js").read_text()
	assert "h(FrappeUIProvider" in mount
	assert 'setConfig("systemTimezone"' in mount
	assert not kit_calls_frappe((SRC / "kit" / "desk.js").read_text()), "call frappe() in the kit"


def test_the_record_page_rules_catch_their_examples():
	assert tabs_down_the_side("<Tabs vertical :tabs>") and not tabs_down_the_side("<Tabs :tabs>")
	assert tabs_stick('<div class="sticky top-0"><ViewTabs /></div>') and not tabs_stick('<div class="sticky"><Button /></div>')
	assert own_view_tabs("<TabTrigger defineProps({ onTitle })") and not own_view_tabs("<ViewTabs")
	assert view_row_lacks("overflow-x-auto flex-nowrap function reveal()") == []
	assert view_row_lacks("<Dropdown") == ["the row scrolls, as a form's tabs do", "no tab is hidden in a menu", "the chosen tab is kept in view"]
	assert own_record_sidebar("__('Assigned To') __(\"Shared With\")") and not own_record_sidebar("__('Assigned To')")
	assert len(switcher_lacks("", "", "")) == 5
	hooks = '"/assets/onedesk/js/panel_menu.js" "/assets/onedesk/js/crumb_switch.js"'
	switch = 'new frappe.ui.Popover({ type="text" frappe.desk.search.search_link onedesk.crumbs.places( onedesk.crumbs.records('
	assert switcher_lacks(hooks, ".body-sidebar .sidebar-items .item-anchor", switch) == []
	assert crumbs_of_its_own("mine.js", "$('.navbar-breadcrumbs')") and not crumbs_of_its_own("crumb_switch.js", "navbar-breadcrumbs")
	css = "@media (max-width: 767.98px) { flex-wrap: wrap !important; flex: 1 0 100%; li.one-crumb-switch:not(:last-child) border-top: 1px solid; height: 44px; li.one-crumb-record }"
	assert phone_head_lacks('"/assets/onedesk/js/phone_head.js"', "--page-head-height search.before(buttons)", css, "one-head-scope one-head-record") == []
	assert len(phone_head_lacks("", "", "", "")) == 8
	assert activity_unlike_a_forms("comment(text)") == ["sends on its own"]
	assert activity_unlike_a_forms("useActivityTimeline( <ActivityTimeline <ActivityComposer <TimelineContainer") == [
		"lacks the composer or Reply and Reply All",
		"has its comment box under the timeline",
		"lists oldest first",
	]
	assert activity_unlike_a_forms("useActivityTimeline( <ActivityComposer composer?.reply(one) composer?.reply(one, true) <ActivityTimeline") == []
	assert kit_calls_frappe("frappe.call()") and not kit_calls_frappe("window.frappe.call()\n// frappe.x")
