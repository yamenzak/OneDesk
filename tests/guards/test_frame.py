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



def islands_unknown(islands, pages) -> list[str]:
	"""The pages of their own with no island, and the islands with no page. Pure."""
	return sorted(set(islands) ^ set(pages))


def test_every_page_is_drawn_by_a_known_island():
	assert not islands_unknown(ISLANDS, tiers.PAGES)


MENU = ("Print", "Email", "Show Links", "Duplicate", "Rename", "Delete", "Remind Me", "Copy to Clipboard")


def page_loses(doctype: str, source: str, desk_page: str, record: str, island_page: str) -> list[str]:
	"""What a record's page of its own loses of its form: its record named for
	frappe's sidebar, the menu, the record heard saved, or a sidebar part drawn
	by the page itself. Pure."""
	out = []
	if f'record: "{doctype}"' not in desk_page:
		out.append("the desk page names its record, for frappe's sidebar")
	for needed, said in (
		("onedesk.record_files.side(frm, open_files)" in record, "record.js lends the files side"),
		(f'useRecord("{doctype}"' in source, "the page uses its record"),
		("record.menu(" in source, "the page has frappe's menu"),
		("follow(" in source, "the page hears the record saved, as a form does"),
		("!!action.standard" in island_page, "island_page keeps frappe's own items"),
	):
		if not needed:
			out.append(said)
	drawn = [one for one in ("Assigned To", "Shared With", "Currently Viewing", "Last Edited By") if one in source]
	if len(drawn) >= 2:
		out.append(f"the page draws its own {', '.join(drawn)}; frappe's sidebar has them")
	return out + [word for word in MENU if f'__("{word}")' not in record]


@pytest.mark.parametrize("doctype", sorted(tiers.PAGES))
def test_a_page_keeps_its_forms_menu_and_sidebar(doctype):
	"""frappe's own form sidebar on the page's right (assigned, attachments,
	tags, shared, likes, viewers, made and changed by), drawn by desk and not
	by the page, and frappe's own menu items under the page's own
	(docs/STANDARD.md, A record's page)."""
	island_page = (APP / "public" / "js" / "island_page.js").read_text()
	found = page_loses(doctype, ISLANDS[doctype].read_text(), DESK_PAGES[doctype].read_text(), RECORD, island_page)
	assert not found, found


def _handle(record: str) -> str:
	return record[record.index("onedesk.record.handle =") : record.index("onedesk.record.said =")]


def handle_misses(record: str, dialogs: list[str], unused=frozenset({"share_doc"})) -> list[str]:
	"""What frappe's dialogs read of a form that record.js's handle lacks. Pure."""
	given = set(re.findall(r"^\t\t(\w+)[,:]", _handle(record), re.M))
	read = set()
	for source in dialogs:
		read |= set(re.findall(r"\b(?:this|me)\.frm\??\.(\w+)", source))
		read |= set(re.findall(r"\bfrm\??\.(\w+)", source))
	return sorted(read - given - unused)


def test_the_record_handle_covers_what_frappes_dialogs_read():
	"""frappe's Share, Email, Links and Remind Me read a form; the handle
	record.js lends them must have every part of one they touch."""
	if not FRAPPE.exists():
		pytest.skip("frappe's source is not beside this checkout")
	found = handle_misses(RECORD, [(FRAPPE / path).read_text() for path in DIALOGS])
	assert not found, found


def stand_in_misses(record: str, sidebar: list[str]) -> list[str]:
	"""What frappe's form sidebar reads of a form that the stand-in lacks and
	does not make, or the sidebar and viewers not made. Pure."""
	stand_in = record[record.index("onedesk.record.sidebar =") :]
	given = set(re.findall(r"^\t\t(\w+)[,:]", _handle(record), re.M)) | set(re.findall(r"^\t\t\t(\w+)[,:]", stand_in, re.M))
	made = {"assign_to", "attachments", "shared", "tags", "sidebar", "viewers"}
	read = set()
	for source in sidebar:
		read |= set(re.findall(r"\bfrm\??\.(\w+)", source))
	out = sorted(read - given - made)
	if not ("new frappe.ui.form.Sidebar(" in stand_in and "new frappe.ui.form.FormViewers(" in stand_in):
		out.append("the stand-in makes no Sidebar and FormViewers")
	return out


def test_the_sidebar_stand_in_covers_what_frappes_sidebar_reads():
	"""frappe's form sidebar and its parts read a form; the stand-in
	onedesk.record.sidebar lends them must have every part of one they touch,
	or they make themselves (assign_to, attachments, shared, tags, sidebar,
	viewers)."""
	if not FRAPPE.exists():
		pytest.skip("frappe's source is not beside this checkout")
	found = stand_in_misses(RECORD, [(FRAPPE / path).read_text() for path in SIDEBAR])
	assert not found, found


def places_unfired(doctype: str, place: str, places: dict, source: str) -> list[str]:
	"""A page with no place for its record, or an event of its place it does
	not fire. Pure."""
	if places.get(place, {}).get("record") != doctype:
		return [f"no place for {doctype}'s page in one_studio/places.py"]
	out = [event for event in places[place]["events"] if f'"{place}.{event}"' not in source]
	return out + ([] if '"record_head.drawn"' in source else ["record_head.drawn"])


@pytest.mark.parametrize("doctype", sorted(tiers.PAGES))
def test_a_page_declares_its_places_and_fires_them(doctype):
	"""A Client Script reaches a form and a list, not a page of One's: the
	page says what an extension may hear on it, and fires it."""
	source = "".join(one.read_text() for one in sorted(ISLANDS[doctype].parent.glob("*.vue")))
	found = places_unfired(doctype, PAGE_PLACES[doctype], _places().PLACES, source)
	assert not found, found


def events_wrong(fired: dict[str, str], listed, runtime: str, hooks: str) -> list[str]:
	"""An event places.py lists that no page fires, one fired that it does
	not list, or a runtime that hands an extension the page's own data. Pure."""
	out = sorted(set(fired) ^ set(listed))
	out += [key for key, source in fired.items() if f'"{key}"' not in source]
	if "JSON.parse(JSON.stringify(data" not in runtime:
		out.append("an extension sees a copy, never the page's own")
	if "onedesk.places.tripped" not in runtime:
		out.append("onedesk.places.tripped")
	if "/assets/onedesk/js/one_studio/places.js" not in hooks:
		out.append("places.js is not loaded")
	return out


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
	found = events_wrong(fired, places.keys(), (public / "one_studio" / "places.js").read_text(), tree.hooks())
	assert not found, found


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


def pages_unknown(pages: dict[str, str], on_the_shell, opens_a_view) -> list[str]:
	"""The pages that are neither an island, one still on the shell, nor one
	that opens a view. Pure."""
	return sorted(name for name, source in pages.items() if name not in on_the_shell and name not in opens_a_view and "onedesk.island_page(" not in source)


def test_every_page_is_an_island_or_still_on_the_shell():
	pages = _pages()
	assert pages, "no pages found"
	unknown = pages_unknown({name: path.read_text(encoding="utf-8") for name, path in pages.items()}, ON_THE_SHELL, OPENS_A_VIEW)
	assert not unknown, (
		"a new page is a Vue island (onedesk.island_page, declared in tiers.SCREENS) or not a page at all: "
		f"frappe's own list or form (onedesk/one_interface/AGENTS.md, the screen contract): {unknown}"
	)


def view_page_does_more(source: str) -> list[str]:
	"""What a page that only opens a view does besides: not replacing its
	route, or drawing. Pure."""
	out = [] if "frappe.set_route(" in source and "frappe.route_flags.replace_route = true" in source else ["does not replace its route"]
	return out + [drawn for drawn in ("make_app_page", "onedesk.shell", ".html(", "$(`") if drawn in source]


def test_a_page_that_opens_a_view_only_opens_it():
	"""It replaces itself with frappe's view (route_flags.replace_route, so
	Back does not land on it again) and makes no page of its own."""
	pages = _pages()
	for name in OPENS_A_VIEW:
		found = view_page_does_more(pages[name].read_text(encoding="utf-8"))
		assert not found, f"{name}: {found}"


def put_on_the_shell(on_the_shell, last) -> list[str]:
	"""The pages on the shell that were not on it at the screen contract. Pure."""
	return sorted(set(on_the_shell) - set(last))


def test_the_shell_only_loses_pages():
	"""No page goes onto the shell any more; one leaves it in the commit that
	moves it, with its old code."""
	found = put_on_the_shell(ON_THE_SHELL, LAST_ON_THE_SHELL)
	assert not found, found


def shell_users(sources: dict[str, str]) -> set[str]:
	"""The files, of those given by path, that call a part of the shell. Pure."""
	return {name for name, source in sources.items() if "onedesk.shell." in source}


def shell_use_moved(using: set[str], known: set[str], shell_left: bool) -> list[str]:
	"""A new user of the shell, a known one that stopped, or the shell left
	behind with nobody using it. Pure."""
	out = [f"new user of the shell: {one}" for one in sorted(using - known)]
	out += [f"no longer uses the shell, take it off USE_THE_SHELL: {one}" for one in sorted(known - using)]
	return out + (["nothing uses the shell: delete shell.js and shell.css"] if not using and shell_left else [])


def test_who_still_uses_the_shell_is_known_and_only_shrinks():
	"""The files that call a part of the shell are exactly USE_THE_SHELL: one
	that stops is taken off it, and none is added. When none is left the
	shell is deleted."""
	using = shell_users(
		{
			str(path.relative_to(tree.APP)): path.read_text(encoding="utf-8")
			for path in tree.APP.rglob("*.js")
			if "public/dist" not in str(path) and path != SHELL_JS
		}
	)
	found = shell_use_moved(using, USE_THE_SHELL, SHELL_JS.exists() or SHELL_CSS.exists())
	assert not found, found


def not_made_by_the_shell(source: str) -> list[str]:
	"""How a page on the shell is not made by it. Pure."""
	out = [] if "onedesk.shell.page(" in source else ["not made by onedesk.shell.page"]
	return out + (["makes its own page"] if "make_app_page" in source else [])


def test_a_page_on_the_shell_is_made_by_it():
	pages = _pages()
	for name in ON_THE_SHELL:
		found = not_made_by_the_shell(pages[name].read_text(encoding="utf-8"))
		assert not found, f"{name}: {found}"


SHELL_PARTS = ("page(", "body(", "name(", "button(", "section(", "row(", "empty(", "quiet(", "class Editor")


def shell_lacks(source: str, hooks: str) -> list[str]:
	"""The parts shell.js lacks, and its files the hooks do not load. Pure."""
	out = [part for part in SHELL_PARTS if part not in source]
	return out + [one for one in ('"/assets/onedesk/js/shell.js"', '"/assets/onedesk/css/shell.css"') if one not in hooks]


def test_the_shell_has_its_parts_and_is_loaded_everywhere():
	found = shell_lacks(SHELL_JS.read_text(encoding="utf-8"), tree.hooks())
	assert not found, found


def restyles_the_shell(css: str) -> list[str]:
	"""The selectors of a stylesheet other than the shell's that end on a
	part of the shell. Pure."""
	out = []
	for line in css.splitlines():
		selector = line.split("{")[0]
		if "{" not in line or ".one-shell" not in selector:
			continue
		if selector.split(",")[-1].strip().split()[-1].startswith(".one-shell"):
			out.append(selector.strip())
	return out


def test_only_the_shell_styles_the_shell():
	for path in tree.scoped(tree.APP.rglob("*.css")):
		if path == SHELL_CSS:
			continue
		found = restyles_the_shell(path.read_text(encoding="utf-8"))
		assert not found, f"{path.name}: {found} restyles the shell"


def draws_shell_parts(css: str, js: str) -> list[str]:
	"""The parts a page on the shell styles or does itself that the shell
	does. Pure."""
	out = sorted({match.group(0) for match in PARTS.finditer(css)} - OWN)
	if re.search(r"(?<![-\w])(min-)?height:\s*calc\(\s*100d?vh", css):
		out.append("sizes itself to the window; use the shell's panes")
	return out + [mark for mark in ("beforeunload", "doc_subscribe", "TimestampMismatchError", "make_app_page", "empty_state(") if mark in js]


def test_a_page_on_the_shell_draws_none_of_its_parts():
	for script, style in set(ON_THE_SHELL.values()):
		css = (tree.APP / style).read_text(encoding="utf-8") if style else ""
		found = draws_shell_parts(css, (tree.APP / script).read_text(encoding="utf-8"))
		assert not found, f"{script}: {found}; the shell does"


OLD_NAMES = re.compile(r"\bos-(row|card|quiet|empty|content|section|actions|chevron|form|columns|part|conflict|alert-row)\b(?!-)")


def test_the_old_names_are_gone():
	"""Settings' parts became the shell's; none of their old names is left."""
	for path in tree.scoped([*tree.APP.rglob("*.js"), *tree.APP.rglob("*.css"), *tree.APP.rglob("*.py")]):
		if "node_modules" in path.parts:
			continue
		found = OLD_NAMES.search(path.read_text(encoding="utf-8"))
		assert not found, f"{path.relative_to(tree.APP)}: {found.group(0)}"


def _page_scripts():
	"""Every script a page of ours is drawn by."""
	return {tree.APP / script for script, _style in ON_THE_SHELL.values()} | set(_pages().values())


RECORD_PARTS = ("trail(", "record($into", "side(", "as_record(", "page.set_breadcrumbs([")


def draws_its_own_record(js: str) -> list[str]:
	"""How a page's script draws a record it opens on itself: a back button,
	shell.name naming a route, or a record read from the address and never
	named with the trail. Pure."""
	out = ["draws its own back button"] if '"arrow-left"' in js or "data-back" in js else []
	out += ["shell.name(..., { route }) names a record; use shell.trail" for call in re.findall(r"shell\.name\(([^;]*)\);", js) if "route:" in call]
	if "get_query_params" in js and "shell.name(" in js and not re.search(r"shell\.trail\(|as_record\(|shell\.record\(", js):
		out.append("opens on a record from its address but never names it with the trail")
	return out


def test_a_record_a_page_opens_on_is_drawn_as_a_docview():
	"""A record a page opens on (a person, a notification type, a document, a
	doctype's customizing, a record's calendar) is named in the breadcrumb
	after its page, "People / Rania Sabbagh", and drawn by the shell's record
	part, never with a head or a back button of its own. docs/SHELL.md, Record."""
	shell = SHELL_JS.read_text(encoding="utf-8")
	assert not [part for part in RECORD_PARTS if part not in shell]
	for path in _page_scripts():
		found = draws_its_own_record(path.read_text(encoding="utf-8"))
		assert not found, f"{path.name}: {found}"


PANE_LISTS = {"record_mail.js"}


def _ours(*patterns):
	for pattern in patterns:
		for path in tree.scoped(tree.APP.rglob(pattern)):
			if "node_modules" in path.parts or "dist" in path.parts:
				continue
			yield path


def own_list(name: str, js: str) -> list[str]:
	"""How a script other than the shell draws a list of records itself: its
	own table, or rows that open records outside a mailbox's pane. Pure."""
	out = ["makes its own table; use onedesk.shell.table"] if "new frappe.ui.EmbeddedList" in js or "embedded_list.bundle" in js else []
	if name in PANE_LISTS:
		return out
	if "one-shell-row-link" in js or re.search(r"\blink:\s*\{", js):
		out.append("a row that opens a record")
	if "shell.list(" in js:
		out.append("a list of rows")
	if any(re.search(r"\b(href|link):", row.group(1)) for row in re.finditer(r"shell\.row\(\{(.*?)\}\)", js, re.S)):
		out.append("a row that opens something")
	if re.search(r"\.map\((?:(?!\.join\().){0,400}?shell\.row\(", js, re.S):
		out.append("a row per record")
	if re.search(r'class="one-shell-(row|list)[" ]', js):
		out.append("draws the shell's rows by hand")
	return out


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
		found = own_list(path.name, path.read_text(encoding="utf-8"))
		assert not found, f"{path.name}: {found}; a list of records is onedesk.shell.table"
	for path in _ours("*.js", "*.css"):
		assert "os-place" not in path.read_text(encoding="utf-8"), f"{path.name} draws sessions by hand"


def own_modal(source: str) -> bool:
	"""Whether a source draws or opens a modal of its own. Pure."""
	return bool(re.search(r"""class=["'][^"']*\bmodal\b""", source)) or "bootstrap.Modal" in source or '.modal("show")' in source


def test_a_dialog_is_frappes():
	"""Every dialog is frappe.ui.Dialog: nothing draws a modal of its own."""
	for path in _ours("*.js", "*.vue", "*.html"):
		assert not own_modal(path.read_text(encoding="utf-8")), f"{path.name} draws its own modal"


CENTRE_FRAME = "centre.js"
"""OneInterface's centre frame (public/js/one_interface/centre.js), the
only script that draws a centre's dialog."""
CREATE = "form.js"
"""A new record in frappe's own form (one_interface/form.js), a dialog of
the create kind, not a centre."""
OWN_CENTRE = re.compile(r"new frappe\.ui\.SettingsDialog\(|extends frappe\.ui\.SettingsDialog\b|new onedesk\.Centre\(|extends onedesk\.Centre\b")
DRAWN = re.compile(r"^(\s*)(?:async\s+)?render(?:\(panel\)|: (?:async )?\(panel\))", re.M)


def own_centres(code: dict[str, str]) -> list[str]:
	"""The scripts that draw a centre's dialog themselves rather than
	declaring it for the frame (`onedesk.centers.declare` and `part`).
	`code` is each script's text by name. Pure."""
	return sorted(name for name, text in code.items() if Path(name).name not in (CENTRE_FRAME, CREATE) and OWN_CENTRE.search(text))


def undeclared_centres(keys: tuple[str, ...], code: str) -> list[str]:
	"""The registry's centres no script declares. Pure."""
	return [key for key in keys if f'onedesk.centers.declare("{key}"' not in code]


def drawn_unsaid(text: str) -> list[int]:
	"""In a script that declares a centre or its part: each section drawn
	by its own `render(panel)` without a docstring just above it saying why
	no declared kind (rows, fields, section, page) fits, by line. Pure."""
	if not re.search(r"onedesk\.centers\.(?:declare|part)\(", text):
		return []
	lines = text.splitlines()
	found = []
	for match in DRAWN.finditer(text):
		at = text.count("\n", 0, match.start())
		before = next((line.strip() for line in reversed(lines[:at]) if line.strip()), "")
		if not before.endswith("*/"):
			found.append(at + 1)
	return found


FITS = (
	".one-centre .settings-dialog-panel-body :has(.embedded-list-table)",
	".one-centre .settings-dialog-panel-body table:not(.embedded-list-table) {\n\twidth: 100%;\n\tmax-width: 100%;\n\ttable-layout: fixed;",
)
"""What keeps every table in a centre inside its frame (centre.css): each box
holding a list's table no wider than the section, and any other table laid
out to the section's width, its words wrapping."""


def unfitted(shell: str, css: str, code: dict[str, str]) -> list[str]:
	"""How a table in a centre could run past the frame (D16): the shell's
	table not folding after it draws and as its frame resizes, folding by its
	own width rather than the room it has, the frame's CSS not holding a table
	to the section, or a script drawing frappe's EmbeddedList itself. Pure."""
	table = shell.split("async table(", 1)[1].split("\n\t},", 1)[0]
	wrong = [f"onedesk.shell.table does not {said}" for part, said in (
		("list.after_render = () => onedesk.shell.fold(list)", "fold after it draws"),
		("new ResizeObserver(() => onedesk.shell.fold(list))", "fold as its frame resizes"),
	) if part not in table]
	if "onedesk.shell.room(wrap)" not in shell.split("fold(list) {", 1)[1].split("\n\t},", 1)[0]:
		wrong.append("onedesk.shell.fold measures the table's own frame, not the room it has")
	wrong += [f"centre.css lost {rule.splitlines()[0]}" for rule in FITS if rule not in css]
	return wrong + [f"{name} draws an EmbeddedList itself; use onedesk.shell.table" for name, text in sorted(code.items()) if "new frappe.ui.EmbeddedList(" in text and not name.endswith("shell.js")]


def test_every_table_in_a_centre_fits_it():
	"""No table in a centre is wider than the frame, at any width, in either
	direction: the shell's table folds a column under the first where it has
	no room (D16), and the frame holds every table to its section."""
	shell = (tree.APP / "public" / "js" / "shell.js").read_text(encoding="utf-8")
	css = (tree.APP / "public" / "css" / "one_interface" / "centre.css").read_text(encoding="utf-8")
	code = {str(path.relative_to(ROOT)): path.read_text(encoding="utf-8") for path in _ours("*.js", "*.vue")}
	assert not unfitted(shell, css, code), unfitted(shell, css, code)


def test_every_centre_opens_in_the_frame():
	"""Every centre is a declaration the frame draws (one_interface/centre.js):
	no script draws a centre's dialog of its own, every centre the registry
	names is declared, and a section that draws its own body says why."""
	from onedesk.one.registry.model import CENTRE_KEYS

	code = {str(path.relative_to(ROOT)): path.read_text(encoding="utf-8") for path in _ours("*.js", "*.vue")}
	assert not own_centres(code), f"draw a centre's dialog of their own; declare it with onedesk.centers.declare: {own_centres(code)}"
	assert not undeclared_centres(CENTRE_KEYS, "\n".join(code.values())), undeclared_centres(CENTRE_KEYS, "\n".join(code.values()))
	unsaid = {name: lines for name, text in code.items() if Path(name).name != CENTRE_FRAME and (lines := drawn_unsaid(text))}
	assert not unsaid, f"a section drawn by its own render with no docstring saying why: {unsaid}"


NEVER_DRAWN = {"me.html", "projects.html", "start.html"}


def off_the_portal(name: str, html: str, py: str) -> list[str]:
	"""How a guest's page is not the portal: a page never drawn or one of
	frappe's that does not redirect, not a web page, not in the portal's
	look, frappe's footer kept, or styled itself. `py` is the page's
	controller. Pure."""
	if name in NEVER_DRAWN or html.lstrip().startswith(f'{{% extends "frappe/www/{name}" %}}'):
		return [] if "frappe.Redirect" in py else ["does not redirect"]
	if name in ("portal.html", "tv.html"):
		return []
	out = [] if html.lstrip().startswith('{% extends "templates/web.html" %}') else ["is not a web page"]
	if 'class="one-portal' not in html and "for-login" not in html:
		out.append("is not in the portal's look")
	if "{%- block footer -%}{%- endblock -%}" not in html:
		out.append("keeps frappe's footer")
	return out + (["styles itself; portal.css does"] if "<style" in html else [])


def test_every_page_outside_the_desk_wears_the_portal():
	"""The pages a guest sees (/start, /welcome, the share and request pages,
	/legal) are frappe's web pages in One's portal look (public/css/one_portal/portal.css),
	without frappe's footer, which says "Powered by ERPNext". The portal
	itself is a frappe-ui app (frontend/portal), whose build writes its page;
	/tv is the TV player, one plain page for an old TV's browser
	(one_display/AGENTS.md)."""
	pages = sorted((tree.APP / "www").glob("*.html"))
	assert pages
	for page in pages:
		if page.name in ("portal.html", "tv.html"):
			continue
		html = page.read_text(encoding="utf-8")
		controller = page.with_suffix(".py") if page.name in NEVER_DRAWN else page.parent / page.name.replace("-", "_").replace(".html", ".py")
		py = controller.read_text(encoding="utf-8") if controller.exists() else ""
		found = off_the_portal(page.name, html, py)
		assert not found, f"{page.name} {found}"


def test_the_frame_rules_catch_their_examples():
	assert own_centres({"a/centre.js": "new frappe.ui.SettingsDialog(", "b/form.js": "new frappe.ui.SettingsDialog(", "c/x.js": "class X extends onedesk.Centre {"}) == ["c/x.js"]
	assert undeclared_centres(("help", "setup"), 'onedesk.centers.declare("help", {})') == ["setup"]
	said = 'onedesk.centers.declare("x", {\n\t/** Why. */\n\trender(panel) {},\n\trender: (panel) => 1,\n});'
	assert drawn_unsaid(said) == [4]
	assert drawn_unsaid("render(panel) {}") == []
	shell = "async table($into) {\n\t\tlist.after_render = () => onedesk.shell.fold(list);\n\t\tnew ResizeObserver(() => onedesk.shell.fold(list))\n\t},\n\tfold(list) {\n\t\tonedesk.shell.room(wrap)\n\t},"
	assert unfitted(shell, "\n".join(FITS), {"a/shell.js": "new frappe.ui.EmbeddedList("}) == []
	assert unfitted(shell.replace("room(wrap)", "x"), "", {"b/c.js": "new frappe.ui.EmbeddedList("}) == [
		"onedesk.shell.fold measures the table's own frame, not the room it has",
		*[f"centre.css lost {rule.splitlines()[0]}" for rule in FITS],
		"b/c.js draws an EmbeddedList itself; use onedesk.shell.table",
	]
	assert islands_unknown({"Task": 1}, {}) == ["Task"] and not islands_unknown({}, {})
	record = 'onedesk.record_files.side(frm, open_files)\n' + "".join(f'__("{word}")' for word in MENU)
	good = 'useRecord("Task" record.menu( follow('
	assert page_loses("Task", good, 'record: "Task"', record, "!!action.standard") == []
	assert page_loses("Task", good + "Assigned To Shared With", "", record, "")
	handle = 'onedesk.record.handle = {\n\t\tdoc,\n\t\treload_doc:\n}\nonedesk.record.said = 1\nonedesk.record.sidebar = {\n\t\t\tdoctype,\n}\nnew frappe.ui.form.Sidebar( new frappe.ui.form.FormViewers('
	assert handle_misses(handle, ["this.frm.doc; frm.reload_doc(); frm.share_doc"]) == []
	assert handle_misses(handle, ["this.frm.save()"]) == ["save"]
	assert stand_in_misses(handle, ["frm.doctype; frm.tags"]) == []
	assert stand_in_misses(handle, ["frm.dirty"]) == ["dirty"]
	places = {"task.page": {"record": "Task", "events": ["shown"]}}
	assert places_unfired("Task", "task.page", places, '"task.page.shown" "record_head.drawn"') == []
	assert places_unfired("Task", "task.page", places, "") == ["shown", "record_head.drawn"]
	assert places_unfired("Item", "task.page", places, "")
	runtime = "JSON.parse(JSON.stringify(data onedesk.places.tripped"
	assert events_wrong({"a.b": '"a.b"'}, ["a.b"], runtime, "/assets/onedesk/js/one_studio/places.js") == []
	assert events_wrong({"a.b": ""}, ["a.b", "c.d"], "", "") == ["c.d", "a.b", "an extension sees a copy, never the page's own", "onedesk.places.tripped", "places.js is not loaded"]
	assert pages_unknown({"stock": "onedesk.island_page(", "mine": "make_app_page", "legal": ""}, {}, {"legal"}) == ["mine"]
	assert view_page_does_more('frappe.route_flags.replace_route = true; frappe.set_route("List")') == []
	assert view_page_does_more("make_app_page") == ["does not replace its route", "make_app_page"]
	assert put_on_the_shell({"onecalendar", "people"}, {"onecalendar"}) == ["people"]
	assert shell_users({"a.js": "onedesk.shell.row(", "b.js": ""}) == {"a.js"}
	assert shell_use_moved({"a.js"}, {"a.js"}, True) == []
	assert len(shell_use_moved({"b.js"}, {"a.js"}, True)) == 2 and shell_use_moved(set(), set(), True)
	assert not_made_by_the_shell("onedesk.shell.page(") == [] and len(not_made_by_the_shell("make_app_page")) == 2
	assert shell_lacks("".join(SHELL_PARTS), '"/assets/onedesk/js/shell.js" "/assets/onedesk/css/shell.css"') == []
	assert shell_lacks("page(", "") == [*SHELL_PARTS[1:], '"/assets/onedesk/js/shell.js"', '"/assets/onedesk/css/shell.css"']
	assert restyles_the_shell(".mine .one-shell-row {") == [".mine .one-shell-row"]
	assert restyles_the_shell(".one-shell-row .mine {") == []
	assert draws_shell_parts(".cal-row { height: calc(100vh - 1px) }", "beforeunload") == [".cal-row", "sizes itself to the window; use the shell's panes", "beforeunload"]
	assert draws_shell_parts(".form-section {}", "") == []
	assert OLD_NAMES.search('class="os-row"') and not OLD_NAMES.search("os-row-x")
	assert draws_its_own_record('icon("arrow-left"); shell.name(x, { route: y });') == ["draws its own back button", "shell.name(..., { route }) names a record; use shell.trail"]
	assert draws_its_own_record("get_query_params(); shell.name(x);") and not draws_its_own_record("get_query_params(); shell.name(x); shell.trail(")
	assert own_list("a.js", "new frappe.ui.EmbeddedList") and own_list("a.js", 'rows.map((r) => shell.row({ label: r }))')
	assert own_list("record_mail.js", "shell.list(") == [] and own_list("a.js", "shell.row({ label: x })") == []
	assert own_modal('<div class="modal fade">') and own_modal('$d.modal("show")') and not own_modal("new frappe.ui.Dialog(")
	portal = '{% extends "templates/web.html" %}<div class="one-portal">{%- block footer -%}{%- endblock -%}'
	assert off_the_portal("welcome.html", portal, "") == []
	assert off_the_portal("welcome.html", "<style>", "") == ["is not a web page", "is not in the portal's look", "keeps frappe's footer", "styles itself; portal.css does"]
	assert off_the_portal("me.html", "", "") == ["does not redirect"]
	assert off_the_portal("login.html", '{% extends "frappe/www/login.html" %}', "raise frappe.Redirect") == []
