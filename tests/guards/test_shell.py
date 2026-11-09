"""The shell is on its way out (onedesk/one_interface/AGENTS.md, the screen contract).

Every screen is one of two kinds: frappe's own list or form, with small
pieces added, or a Vue island, for a screen that is more than a list or a
form. Our own JavaScript pages on `onedesk.shell` go away, each in the
commit that moves it, so the two lists here only shrink, and the shell
itself goes when they are empty. Until a page moves it keeps the shell's
rules: its head is frappe's page head, its body the shell's column or wide,
and its sections, rows, empty states and quiet lines are the shell's.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import tree

SHELL_JS = tree.APP / "public" / "js" / "shell.js"
SHELL_CSS = tree.APP / "public" / "css" / "shell.css"
HOOKS = (tree.APP / "hooks.py").read_text(encoding="utf-8")

ON_THE_SHELL = {
	"onecalendar": (
		"one_calendar/page/onecalendar/onecalendar.js",
		"one_calendar/page/onecalendar/onecalendar.css",
	),
}

# The pages on the shell when the contract was written; the list above only
# ever loses one.
WERE_ON_THE_SHELL = {"settings", "workspace_settings", "legal", "intake", "ready_to_submit", "onecalendar", "onemail", "onecloud", "masters"}

# Every file that still calls a part of the shell. It only shrinks too; when
# it is empty, shell.js and shell.css are deleted. A section that moved out
# of Settings into a centre took its drawing with it (docs/ONE.md, stage 2)
# until One's screens are drawn again (stage 8): center_section.js and the
# files below it that draw a centre's tabs.
USE_THE_SHELL = {
	"public/js/center_section.js",
	"public/js/one/access_center.js",
	"public/js/one_ai/ai_center.js",
	"public/js/one/one_control.js",
	"public/js/one_hr/hr_control.js",
	"public/js/one_studio/studio_control.js",
	"public/js/one/notification_center.js",
	"one_calendar/page/onecalendar/onecalendar.js",
	"public/js/one_account/account_center.js",
	"public/js/band.js",
	"public/js/calendar_link.js",
	"public/js/desk.js",
	"public/js/doctype_settings.js",
	"public/js/extension_errors.js",
	"public/js/island_page.js",
	"public/js/one_mail/record_mail.js",
	"public/js/one_interface/frame.js",
}

# Addresses that only open a frappe view in their own place (a rail's or a
# home's link), or a center over the desk, and draw nothing.
OPENS_A_VIEW = {"legal"}

ISLAND_PAGES = {"oneadmin_sessions", "oneadmin_status", "oneadmin_billing", "oneadmin_releases", "oneadmin", "oneadmin_servers", "one", "recycle_bin", "announcements", "address_book", "stock_on_hand", "inventory", "books", "onecrm", "onehr", "lots", "to_order", "quotes", "sent_out", "upkeep", "floor", "onefactory", "onequality", "plant", "my_tasks", "timers", "counter", "boards", "workbook", "document", "presentation", "intake", "onemail", "onecloud"}

PARTS = re.compile(r"\.[a-z]+-(row|empty|quiet|card|content|section|chevron)(-[a-z]+)?\b(?![-\w])")

OWN = {".os-people-row", ".form-section"}


def _pages():
	return {
		path.parent.name: path for path in tree.APP.glob("*/page/*/*.js") if path.stem == path.parent.name
	}


def test_every_page_is_an_island_or_still_on_the_shell():
	pages = _pages()
	assert pages, "no pages found"
	unknown = set(pages) - set(ON_THE_SHELL) - ISLAND_PAGES - OPENS_A_VIEW
	assert not unknown, (
		"a new page is a Vue island (ISLAND_PAGES, declared in tiers.SCREENS) or not a page at all: "
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
	assert set(ON_THE_SHELL) <= WERE_ON_THE_SHELL, sorted(set(ON_THE_SHELL) - WERE_ON_THE_SHELL)


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
	assert '"/assets/onedesk/js/shell.js"' in HOOKS
	assert '"/assets/onedesk/css/shell.css"' in HOOKS


def test_only_the_shell_styles_the_shell():
	for path in tree.APP.rglob("*.css"):
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
	for path in [*tree.APP.rglob("*.js"), *tree.APP.rglob("*.css"), *tree.APP.rglob("*.py")]:
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
		for path in tree.APP.rglob(pattern):
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
