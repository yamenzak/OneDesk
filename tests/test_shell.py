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
}

#: Pages not on it yet, and the stage of docs/SHELL.md that moves them. A new
#: page is in neither, and fails until it is on the shell.
NOT_YET = {
	"onemail": 3,
	"onecloud": 3,
}

#: What the shell has, so a page may not style its own: a row of a list, an
#: empty state, a quiet line, a boxed card, a body or a section.
PARTS = re.compile(r"\.[a-z]+-(row|empty|quiet|card|content|section|chevron)(-[a-z]+)?\b(?![-\w])")

#: A page's own part that shares a name with the shell's but is not one: the
#: People section's grid row is a row of a table, not of a list.
OWN = {".os-people-row"}


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
		css = (tree.APP / style).read_text(encoding="utf-8")
		own = {match.group(0) for match in PARTS.finditer(css)} - OWN
		assert not own, f"{style} styles its own {sorted(own)}; use the shell's"
		# The one place a page is sized to the window is the shell's fit().
		assert not re.search(r"\d+d?vh", css), f"{style} sizes itself to the window; use the shell's panes"
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
