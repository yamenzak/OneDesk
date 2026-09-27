"""Every page of ours is built in the shell (docs/SHELL.md).

A page composes the shell's parts rather than drawing its own: its head is
frappe's page head, its body the shell's column or wide, and its sections,
rows, empty states and quiet lines are the shell's, styled once in
`public/css/shell.css`. A record edited on a page is the shell's Editor, so
dirty, leaving, saving against `modified` and hearing another save are written
once. These fail when a page draws a part the shell has.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

SHELL_JS = tree.APP / "public" / "js" / "shell.js"
SHELL_CSS = tree.APP / "public" / "css" / "shell.css"
HOOKS = (tree.APP / "hooks.py").read_text(encoding="utf-8")

#: Pages on the shell: their page script makes the page with
#: `onedesk.shell.page`, and what draws them uses its parts.
ON_THE_SHELL = {
	"settings": ("public/js/settings.js", "public/css/settings.css"),
	"workspace_settings": ("public/js/settings.js", "public/css/settings.css"),
	"my_tasks": ("one_task/page/my_tasks/my_tasks.js", "one_task/page/my_tasks/my_tasks.css"),
	"legal": ("one_legal/page/legal/legal.js", "public/css/legal.css"),
	"intake": ("one_intake/page/intake/intake.js", "public/css/intake.css"),
	"ready_to_submit": ("one_intake/page/ready_to_submit/ready_to_submit.js", "public/css/intake.css"),
	"onecalendar": (
		"one_calendar/page/onecalendar/onecalendar.js",
		"one_calendar/page/onecalendar/onecalendar.css",
	),
	"onemail": ("public/js/onemail.js", "public/css/onemail.css"),
	"onecloud": ("public/js/onecloud.js", "public/css/onecloud.css"),
	# Nothing of its own to style: every part is the shell's or frappe's.
	"customize": ("public/js/customize.js", None),
}

#: Pages not on it yet, and the stage of docs/SHELL.md that moves them. None
#: is left; a new page is in neither, and fails until it is on the shell.
NOT_YET = {}

#: What the shell has, so a page may not style its own: a row of a list, an
#: empty state, a quiet line, a boxed card, a body or a section.
PARTS = re.compile(r"\.[a-z]+-(row|empty|quiet|card|content|section|chevron)(-[a-z]+)?\b(?![-\w])")

#: A part that shares a name with the shell's but is not one: the People
#: section's grid row is a row of a table, not of a list, and a record's Files
#: tab sits in frappe's own form section.
OWN = {".os-people-row", ".form-section"}


def _pages():
	return {
		path.parent.name: path for path in tree.APP.glob("*/page/*/*.js") if path.stem == path.parent.name
	}


def test_every_page_is_on_the_shell_or_named_as_not_yet():
	pages = _pages()
	assert pages, "no pages found"
	unknown = set(pages) - set(ON_THE_SHELL) - set(NOT_YET)
	assert not unknown, f"a new page goes on the shell (onedesk.shell.page): {sorted(unknown)}"
	assert not set(ON_THE_SHELL) & set(NOT_YET)


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
			# A page may place its own part inside one of the shell's, never
			# restyle the shell's part itself.
			last = selector.split(",")[-1].strip().split()[-1]
			assert not last.startswith(".one-shell"), f"{path.name}: {selector.strip()} restyles the shell"


def test_a_page_on_the_shell_draws_none_of_its_parts():
	for script, style in set(ON_THE_SHELL.values()):
		css = (tree.APP / style).read_text(encoding="utf-8") if style else ""
		own = {match.group(0) for match in PARTS.finditer(css)} - OWN
		assert not own, f"{style} styles its own {sorted(own)}; use the shell's"
		# The one place a page is sized to the window is the shell's fit().
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


#: The one back button left is OneCloud's, and it is the explorer's own
#: history (back to the folder you came from), not a way out of a page.
BACK_ALLOWED = {"onecloud.js"}


def _page_scripts():
	"""Every script a page of ours is drawn by."""
	return {tree.APP / script for script, _style in ON_THE_SHELL.values()} | set(_pages().values())


def test_a_record_a_page_opens_on_is_drawn_as_a_docview():
	"""A record a page opens on (a person, a notification type, a document, a
	doctype's customizing, a record's calendar) is named in the breadcrumb
	after its page, "People / Rania Sabbagh", and drawn by the shell's record
	part, never with a head or a back button of its own. docs/SHELL.md, Record."""
	shell = SHELL_JS.read_text(encoding="utf-8")
	for part in ("trail(", "record($into", "side(", "as_record(", "then: esc(label)"):
		assert part in shell, part
	for path in _page_scripts():
		js = path.read_text(encoding="utf-8")
		# A way out of a page is the breadcrumb, not a button in it.
		if path.name not in BACK_ALLOWED:
			assert '"arrow-left"' not in js and "data-back" not in js, f"{path.name} draws its own back button"
		# Naming a page after something inside another is the trail's job.
		for call in re.findall(r"shell\.name\(([^;]*)\);", js):
			assert "route:" not in call, f"{path.name}: shell.name(..., {{ route }}) names a record; use shell.trail"
		# A page that opens on something from its address, and names itself,
		# names that something through the trail.
		if "get_query_params" in js and "shell.name(" in js:
			assert re.search(r"shell\.trail\(|as_record\(|shell\.record\(", js), (
				f"{path.name} opens on a record from its address but never names it with the trail"
			)


#: Lists whose rows open what they are in the pane beside them: a mailbox,
#: and OneIntake's reading list. Every other list of records is a table.
PANE_LISTS = {"onemail.js", "intake.js", "record_mail.js"}


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
	for path in _ours("*.js", "*.css"):
		assert "os-place" not in path.read_text(encoding="utf-8"), f"{path.name} draws sessions by hand"


def test_a_dialog_is_frappes():
	"""Every dialog is frappe.ui.Dialog: nothing draws a modal of its own."""
	for path in _ours("*.js", "*.vue", "*.html"):
		source = path.read_text(encoding="utf-8")
		assert not re.search(r"""class=["'][^"']*\bmodal\b""", source), f"{path.name} draws its own modal"
		assert "bootstrap.Modal" not in source and '.modal("show")' not in source, f"{path.name} opens its own modal"


def test_every_page_outside_the_desk_wears_the_portal():
	"""The pages a customer or a guest sees (/start, /welcome, the share and
	request pages, a customer's project) are frappe's web pages in One's
	portal look (public/css/portal.css), without frappe's footer, which says
	"Powered by ERPNext"."""
	pages = sorted((tree.APP / "www").glob("*.html"))
	assert pages
	for page in pages:
		html = page.read_text(encoding="utf-8")
		assert html.lstrip().startswith('{% extends "templates/web.html" %}'), f"{page.name} is not a web page"
		assert 'class="one-portal' in html, f"{page.name} is not in the portal's look"
		assert "{%- block footer -%}{%- endblock -%}" in html, f"{page.name} keeps frappe's footer"
		assert "<style" not in html, f"{page.name} styles itself; portal.css does"
