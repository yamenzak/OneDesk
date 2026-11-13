"""Points 6 and 7: a desk page of ours and the frame it is drawn in.

Every page is a Vue island (onedesk.island_page), a page that only opens a
frappe view, or one still on the shell (onedesk/one_interface/AGENTS.md, the
screen contract); which page is which is read from its code, and tiers.SCREENS
is the one list of pages (test_tiers.py). The shell's pages only leave it, each
in the commit that moves it, and the files calling a part of the shell only
shrink: shell.js and shell.css go when none is left. Until then a page on the
shell keeps its rules: its head is frappe's page head, its body the shell's
column or wide, and its sections, rows, empty states and quiet lines the
shell's.

A record on a page of its own (onedesk/one/tiers.py PAGES) loses nothing its
form has, and the workspace's extensions reach it. A page outside the desk
wears the portal."""

import importlib.util
import re
from pathlib import Path

import pytest

from onedesk.one import tiers
from tests.bench import APPS
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import tree  # noqa: E402

SHELL_JS = tree.APP / "public" / "js" / "shell.js"
SHELL_CSS = tree.APP / "public" / "css" / "shell.css"

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "onedesk"
RECORD = (APP / "public" / "js" / "record.js").read_text()
FRAPPE = APPS / "frappe/frappe/public/js/frappe"

ISLANDS = {}
DESK_PAGES = {}

PAGE_PLACES = {}

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
	(docs/STANDARD.md, A record's page)."""
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
		"onecrm.board": (public / "one_crm" / "opportunity_list.js").read_text(),
		"space.home": (public / "one_studio" / "places.js").read_text(),
		**{
			f"oneproject.{view}": (ROOT / "frontend" / "src" / "project" / f"{name}.vue").read_text()
			for view, name in (
				("overview", "Overview"),
				("time", "Time"),
				("money", "Money"),
				("invoices", "Invoices"),
				("suppliers", "Suppliers"),
				("team", "Team"),
			)
		},
		**{
			f"oneinventory_item.{view}": (ROOT / "frontend" / "src" / "inventory" / "item" / f"{name}.vue").read_text()
			for view, name in (
				("stock", "ItemStock"),
				("buying", "ItemBuying"),
				("selling", "ItemSelling"),
				("making", "ItemMaking"),
			)
		},
		"oneinventory_stock.on_hand": (ROOT / "frontend" / "src" / "inventory" / "stock" / "StockOnHand.vue").read_text(),
		"onefactory_floor.shown": (ROOT / "frontend" / "src" / "factory" / "floor" / "ShopFloor.vue").read_text(),
		"onequality_home.shown": (ROOT / "frontend" / "src" / "quality" / "QualityHome.vue").read_text(),
		"onefactory_home.shown": (ROOT / "frontend" / "src" / "factory" / "home" / "FactoryHome.vue").read_text(),
		"oneinventory_home.shown": (ROOT / "frontend" / "src" / "inventory" / "home" / "InventoryHome.vue").read_text(),
		"onecrm_home.shown": (ROOT / "frontend" / "src" / "crm" / "CrmHome.vue").read_text(),
		"onehr_home.shown": (ROOT / "frontend" / "src" / "hr" / "HrHome.vue").read_text(),
		"onebook_home.shown": (ROOT / "frontend" / "src" / "books" / "BooksHome.vue").read_text(),
		"oneinventory_order.shown": (ROOT / "frontend" / "src" / "inventory" / "to_order" / "ToOrderPage.vue").read_text(),
		"oneproject_workload.week": (APP / "one_project" / "report" / "workload" / "workload.js").read_text(),
		"oneproject_list.projects": (APP / "public" / "js" / "one_project" / "project_list.js").read_text(),
	}
	assert set(fired) == set(places.keys())
	for key, source in fired.items():
		assert f'"{key}"' in source, key
	runtime = (public / "one_studio" / "places.js").read_text()
	assert "JSON.parse(JSON.stringify(data" in runtime, "an extension sees a copy, never the page's own"
	assert "onedesk.places.tripped" in runtime
	assert "/assets/onedesk/js/one_studio/places.js" in tree.hooks()


ON_THE_SHELL = {
	"onecalendar": (
		"one_calendar/page/onecalendar/onecalendar.js",
		"one_calendar/page/onecalendar/onecalendar.css",
	),
}

LAST_ON_THE_SHELL = {"onecalendar"}

USE_THE_SHELL = {
	"public/js/center_section.js",
	"public/js/one/access_center.js",
	"public/js/one_ai/ai_center.js",
	"public/js/one/one_control.js",
	"public/js/one_hr/hr_control.js",
	"public/js/one_studio/studio_control.js",
	"public/js/one/notification_center.js",
	"one_calendar/page/onecalendar/onecalendar.js",
	"public/js/account_center/account_center.js",
	"public/js/band.js",
	"public/js/one_calendar/calendar_link.js",
	"public/js/desk.js",
	"public/js/doctype_settings.js",
	"public/js/one_studio/extension_errors.js",
	"public/js/island_page.js",
	"public/js/one_mail/record_mail.js",
	"public/js/one_interface/frame.js",
}

OPENS_A_VIEW = {"legal"}

PARTS = re.compile(r"\.[a-z]+-(row|empty|quiet|card|content|section|chevron)(-[a-z]+)?\b(?![-\w])")

OWN = {".os-people-row", ".form-section"}


def _pages():
	return {
		path.parent.name: path for path in tree.APP.glob("*/page/*/*.js") if path.stem == path.parent.name
	}


def test_every_page_is_an_island_or_still_on_the_shell():
	pages = _pages()
	assert pages, "no pages found"
	unknown = {
		name
		for name, path in pages.items()
		if name not in ON_THE_SHELL and name not in OPENS_A_VIEW and "onedesk.island_page(" not in path.read_text(encoding="utf-8")
	}
	assert not unknown, (
		"a new page is a Vue island (onedesk.island_page, declared in tiers.SCREENS) or not a page at all: "
		f"frappe's own list or form (onedesk/one_interface/AGENTS.md, the screen contract): {sorted(unknown)}"
	)


def test_a_page_that_opens_a_view_only_opens_it():
	"""It replaces itself with frappe's view (route_flags.replace_route, so
	Back does not land on it again) and makes no page of its own."""
	pages = _pages()
	for name in OPENS_A_VIEW:
		source = pages[name].read_text(encoding="utf-8")
		assert "frappe.set_route(" in source and "frappe.route_flags.replace_route = true" in source, name
		for drawn in ("make_app_page", "onedesk.shell", ".html(", "$(`"):
			assert drawn not in source, f"{name} draws: {drawn}"


def test_the_shell_only_loses_pages():
	"""No page goes onto the shell any more; one leaves it in the commit that
	moves it, with its old code."""
	assert set(ON_THE_SHELL) <= LAST_ON_THE_SHELL, sorted(set(ON_THE_SHELL) - LAST_ON_THE_SHELL)


def test_who_still_uses_the_shell_is_known_and_only_shrinks():
	"""The files that call a part of the shell are exactly USE_THE_SHELL: one
	that stops is taken off it, and none is added. When none is left the
	shell is deleted."""
	using = {
		str(path.relative_to(tree.APP))
		for path in tree.APP.rglob("*.js")
		if "public/dist" not in str(path) and path != SHELL_JS and "onedesk.shell." in path.read_text(encoding="utf-8")
	}
	assert using <= USE_THE_SHELL, f"new users of the shell: {sorted(using - USE_THE_SHELL)}"
	assert USE_THE_SHELL <= using, f"no longer use the shell, take them off USE_THE_SHELL: {sorted(USE_THE_SHELL - using)}"
	if not using:
		assert not SHELL_JS.exists() and not SHELL_CSS.exists(), "nothing uses the shell: delete shell.js and shell.css"


def test_a_page_on_the_shell_is_made_by_it():
	pages = _pages()
	for name in ON_THE_SHELL:
		source = pages[name].read_text(encoding="utf-8")
		assert "onedesk.shell.page(" in source, name
		assert "make_app_page" not in source, f"{name} makes its own page"


def test_the_shell_has_its_parts_and_is_loaded_everywhere():
	source = SHELL_JS.read_text(encoding="utf-8")
	for part in (
		"page(",
		"body(",
		"name(",
		"button(",
		"section(",
		"row(",
		"empty(",
		"quiet(",
		"class Editor",
	):
		assert part in source, part
	assert '"/assets/onedesk/js/shell.js"' in tree.hooks()
	assert '"/assets/onedesk/css/shell.css"' in tree.hooks()


def test_only_the_shell_styles_the_shell():
	for path in tree.scoped(tree.APP.rglob("*.css")):
		if path == SHELL_CSS:
			continue
		for line in path.read_text(encoding="utf-8").splitlines():
			selector = line.split("{")[0]
			if "{" not in line or ".one-shell" not in selector:
				continue
			last = selector.split(",")[-1].strip().split()[-1]
			assert not last.startswith(".one-shell"), f"{path.name}: {selector.strip()} restyles the shell"


def test_a_page_on_the_shell_draws_none_of_its_parts():
	for script, style in set(ON_THE_SHELL.values()):
		css = (tree.APP / style).read_text(encoding="utf-8") if style else ""
		own = {match.group(0) for match in PARTS.finditer(css)} - OWN
		assert not own, f"{style} styles its own {sorted(own)}; use the shell's"
		assert not re.search(r"(?<![-\w])(min-)?height:\s*calc\(\s*100d?vh", css), (
			f"{style} sizes itself to the window; use the shell's panes"
		)
		js = (tree.APP / script).read_text(encoding="utf-8")
		for mark in (
			"beforeunload",
			"doc_subscribe",
			"TimestampMismatchError",
			"make_app_page",
			"empty_state(",
		):
			assert mark not in js, f"{script} does {mark} itself; the shell does"


def test_the_old_names_are_gone():
	"""Settings' parts became the shell's; none of their old names is left."""
	old = re.compile(
		r"\bos-(row|card|quiet|empty|content|section|actions|chevron|form|columns|part|conflict|alert-row)\b(?!-)"
	)
	for path in tree.scoped([*tree.APP.rglob("*.js"), *tree.APP.rglob("*.css"), *tree.APP.rglob("*.py")]):
		if "node_modules" in path.parts:
			continue
		found = old.search(path.read_text(encoding="utf-8"))
		assert not found, f"{path.relative_to(tree.APP)}: {found.group(0)}"


def _page_scripts():
	"""Every script a page of ours is drawn by."""
	return {tree.APP / script for script, _style in ON_THE_SHELL.values()} | set(_pages().values())


def test_a_record_a_page_opens_on_is_drawn_as_a_docview():
	"""A record a page opens on (a person, a notification type, a document, a
	doctype's customizing, a record's calendar) is named in the breadcrumb
	after its page, "People / Rania Sabbagh", and drawn by the shell's record
	part, never with a head or a back button of its own. docs/SHELL.md, Record."""
	shell = SHELL_JS.read_text(encoding="utf-8")
	for part in ("trail(", "record($into", "side(", "as_record(", "page.set_breadcrumbs(["):
		assert part in shell, part
	for path in _page_scripts():
		js = path.read_text(encoding="utf-8")
		assert '"arrow-left"' not in js and "data-back" not in js, f"{path.name} draws its own back button"
		for call in re.findall(r"shell\.name\(([^;]*)\);", js):
			assert "route:" not in call, f"{path.name}: shell.name(..., {{ route }}) names a record; use shell.trail"
		if "get_query_params" in js and "shell.name(" in js:
			assert re.search(r"shell\.trail\(|as_record\(|shell\.record\(", js), (
				f"{path.name} opens on a record from its address but never names it with the trail"
			)


PANE_LISTS = {"record_mail.js"}


def _ours(*patterns):
	for pattern in patterns:
		for path in tree.scoped(tree.APP.rglob(pattern)):
			if "node_modules" in path.parts or "dist" in path.parts:
				continue
			yield path


def test_a_list_of_records_is_frappes_table():
	"""A list of records a person searches or opens is the shell's table,
	frappe's EmbeddedList, made in one place; a row that opens something is
	only a mailbox's, in its pane. Sessions and sign-ins are tables too, never
	lines drawn by hand. docs/SHELL.md, Lists."""
	shell = SHELL_JS.read_text(encoding="utf-8")
	assert "table($into" in shell and "new frappe.ui.EmbeddedList" in shell
	for path in _ours("*.js"):
		if path == SHELL_JS:
			continue
		js = path.read_text(encoding="utf-8")
		assert "new frappe.ui.EmbeddedList" not in js and "embedded_list.bundle" not in js, (
			f"{path.name} makes its own table; use onedesk.shell.table"
		)
		if path.name not in PANE_LISTS:
			assert "one-shell-row-link" not in js and not re.search(r"\blink:\s*\{", js), (
				f"{path.name}: a row that opens a record; a list of records is onedesk.shell.table"
			)
			assert "shell.list(" not in js, f"{path.name}: a list of rows; a list of records is onedesk.shell.table"
			for row in re.finditer(r"shell\.row\(\{(.*?)\}\)", js, re.S):
				assert not re.search(r"\b(href|link):", row.group(1)), (
					f"{path.name}: a row that opens something; a list of records is onedesk.shell.table"
				)
			assert not re.search(r"\.map\((?:(?!\.join\().){0,400}?shell\.row\(", js, re.S), (
				f"{path.name}: a row per record; a list of records is onedesk.shell.table"
			)
			assert not re.search(r'class="one-shell-(row|list)[" ]', js), (
				f"{path.name} draws the shell's rows by hand; one fact is onedesk.shell.row, many are onedesk.shell.table"
			)
	for path in _ours("*.js", "*.css"):
		assert "os-place" not in path.read_text(encoding="utf-8"), f"{path.name} draws sessions by hand"


def test_a_dialog_is_frappes():
	"""Every dialog is frappe.ui.Dialog: nothing draws a modal of its own."""
	for path in _ours("*.js", "*.vue", "*.html"):
		source = path.read_text(encoding="utf-8")
		assert not re.search(r"""class=["'][^"']*\bmodal\b""", source), f"{path.name} draws its own modal"
		assert "bootstrap.Modal" not in source and '.modal("show")' not in source, f"{path.name} opens its own modal"


def test_every_page_outside_the_desk_wears_the_portal():
	"""The pages a guest sees (/start, /welcome, the share and request pages,
	/legal) are frappe's web pages in One's portal look (public/css/one_portal/portal.css),
	without frappe's footer, which says "Powered by ERPNext". The portal
	itself is a frappe-ui app (frontend/portal), whose build writes its page;
	/tv is the TV player, one plain page for an old TV's browser
	(one_display/AGENTS.md)."""
	pages = sorted((tree.APP / "www").glob("*.html"))
	assert pages
	never_drawn = {"me.html", "projects.html"}
	for page in pages:
		if page.name in never_drawn:
			assert "frappe.Redirect" in page.with_suffix(".py").read_text(encoding="utf-8")
			continue
		if page.name in ("portal.html", "tv.html"):
			continue
		html = page.read_text(encoding="utf-8")
		frappes = f'{{% extends "frappe/www/{page.name}" %}}'
		if html.lstrip().startswith(frappes):
			assert "frappe.Redirect" in (page.parent / page.name.replace("-", "_").replace(".html", ".py")).read_text()
			continue
		assert html.lstrip().startswith('{% extends "templates/web.html" %}'), f"{page.name} is not a web page"
		assert 'class="one-portal' in html or "for-login" in html, f"{page.name} is not in the portal's look"
		assert "{%- block footer -%}{%- endblock -%}" in html, f"{page.name} keeps frappe's footer"
		assert "<style" not in html, f"{page.name} styles itself; portal.css does"
