"""Every screen of ours is drawn in frappe-ui's tokens, so it looks like one
product in either theme. A colour is an `--ink-*`, `--surface-*` or
`--outline-*` token (or one of ours named `--one-*`, made of them); a corner is
a `--radius-*`; a border is 1px of one of those colours; and nothing of ours
casts a shadow. A literal colour, a fallback, frappe's older names
(`--text-color`, `--border-color`, the `--gray-500` ramp) and Tailwind's raw
palette (`bg-gray-100`) each bypass the theme, which is how one page came out
grey and the next blue. The One mark's own colours are the one exception.
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import tree

FRONTEND = tree.ROOT / "frontend" / "src"

# Drawn where frappe-ui's tokens are not loaded: a print, a mail, and the TV
# player and the designed slides it draws, which load no stylesheet of
# frappe's to fit an old TV's memory (one_display/AGENTS.md).
NOT_A_SCREEN = ("one_print", "print_format", "letter_head", "/notifications/", "templates/emails", "www/tv.html", "one_display/blocks.js")

SANDBOXED = {
	"frontend/src/mail/mail.js": "a received mail, in a frame",
	"onedesk/public/js/one_studio/studio_control.js": "a letter head as it prints, in a frame",
	"onedesk/public/js/one_mail/onemail_settings.js": "a signature as it sends, in a frame",
	"onedesk/public/js/one_mail/mail_compose.js": "a signature as it sends, in a frame",
}

MARK = re.compile(r"--one-(suite|ai|over)-[\w-]+")

OVER = {
	f"{tone}-{step}": f"oklch({1 if tone == 'white' else 0} 0 0 / {alpha})"
	for tone in ("white", "black")
	for step, alpha in (
		("100", "0.18"),
		("200", "0.271"),
		("300", "0.361"),
		("500", "0.541"),
		("700", "0.722"),
		("900", "0.898"),
		("950", "0.949"),
	)
}

HUES = "amber|blue|cyan|green|orange|pink|purple|red|teal|violet|yellow"
TOKEN = re.compile(
	rf"--(ink|surface|outline)-({HUES})-(10|[1-9])|--(ink|outline)-gray-[1-9]|--surface-gray-(10|[1-9])"
	r"|--(ink|surface|outline)-base|--surface-sidebar|--surface-elevation-[1-3]|--outline-elevation-[12]|--ink-blue-link"
	r"|--(surface|outline)-alpha-[\w-]+|--focus-outline-(amber|blue|default|green|red|violet)"
	r"|--one-[\w-]+|--desk-sidebar-bg"
)

RADIUS = re.compile(r"var\(--radius(-(sm|md|lg|xl|2xl|full|none|[0-9]))?\)")

OLD = re.compile(
	r"--(text-(color|muted|light|extra-muted|on-[\w-]+)|bg-[\w-]+|border-color|fg-color|card-bg|subtle-[\w-]+|control-bg|btn-[\w-]+|heading-color"
	r"|white|black|shadow[\w-]*|elevation-[\w-]+|dock-[\w-]+|(gray|blue|green|red|orange|amber|yellow|teal|cyan"
	r"|violet|purple|pink|neutral)-\d+)"
)

LITERAL = re.compile(r"#[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?|oklch|oklab|lab|lch|color)\(")
NAMED = re.compile(
	r"(?<![\w-])(white|black|red|blue|green|gray|grey|silver|orange|yellow|purple|pink)(?![\w-])"
)
COLOURED = re.compile(
	r"(color|background(-color|-image)?|border(-(top|right|bottom|left|inline|block)(-(start|end))?)?(-color)?"
	r"|outline(-color)?|fill|stroke|stop-color|caret-color|accent-color|text-decoration(-color)?|column-rule)"
)
SIDE = r"(-(top|right|bottom|left|inline|block)(-(start|end))?)?"
DECL = re.compile(r"(?<![\w-])(-?-?[a-z][\w-]*)\s*:\s*([^;{}]+?)\s*(?:;|(?=\})|$)", re.S)

PALETTE = re.compile(
	r"(?<![\w-])(?:[a-z-]+:)*(?:bg|text|border|ring|fill|stroke|from|via|to|divide|outline|decoration|placeholder"
	r"|caret|accent)-(?:(?:gray|slate|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue"
	r"|indigo|violet|purple|fuchsia|pink|rose)-\d{2,3}|white|black)(?:/\d+)?(?![\w-])"
)
ARBITRARY = re.compile(
	r"(?<![\w-])(?:[a-z-]+:)*(?:rounded(?:-[trblse]{1,2})?|border(?:-[trblxy])?|shadow|drop-shadow|bg|text|ring|outline"
	r"|fill|stroke|from|via|to)-\[(?:#|rgb|hsl|oklch|\d|var|calc)[^\]]*\]"
)
WIDE = re.compile(r"(?<![\w-])(?:[a-z-]+:)*border(?:-[trblxy])?-(?:2|4|8)(?![\w-])")
SHADOW = re.compile(
	r"(?<![\w-])(?:[a-z-]+:)*(?:shadow(?:-(?!none(?![\w-]))[a-z0-9]+)?|drop-shadow(?:-[a-z0-9]+)?)(?![\w-])"
)
QUOTED = re.compile(r"""["'`]\s*(#[0-9a-fA-F]{3,8}|(?:rgba?|hsla?|oklch)\([^)]*\))\s*["'`]""")
CLASSES = re.compile(
	r"""(?<![\w-])(?::?class)\s*=\s*"([^"]*)"|class:\s*["'`]([^"'`]*)["'`]|classList\.\w+\(([^)]*)\)"""
)


def _screens() -> list[Path]:
	found = [p for p in tree._walk() if p.suffix in {".css", ".js", ".html", ".vue"}]
	for root in (FRONTEND, FRONTEND.parent / "portal" / "src"):
		found += [p for p in sorted(root.rglob("*")) if p.is_file() and p.suffix in {".css", ".js", ".ts", ".vue"}]
	return [p for p in found if not any(part in str(p) for part in NOT_A_SCREEN) and not tree.vendored(p)]


def _css(path: Path, text: str):
	"""The CSS in a file: all of a stylesheet, a component's <style>, and every
	style attribute."""
	text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
	if path.suffix == ".css":
		yield text
		return
	for found in re.finditer(r"<style[^>]*>(.*?)</style>", text, re.S):
		yield found.group(1)
	for found in re.finditer(r"""(?<![:\w])style\s*=\s*(["'])(.*?)\1""", text, re.S):
		yield found.group(2)


def _vars(value: str) -> list[str]:
	return re.findall(r"var\(\s*(--[\w-]+)", value)


def declaration(prop: str, value: str) -> list[str]:
	"""What is wrong with one declaration, in words; nothing when it is right."""
	prop, value = prop.lower(), value.replace("!important", "").strip()
	wrong = []
	if prop.startswith("--"):
		if not MARK.fullmatch(prop):
			if LITERAL.search(value):
				wrong.append("a literal colour in a token: make it of frappe-ui's tokens")
			wrong += [f"{name} is not a frappe-ui token" for name in _vars(value) if OLD.fullmatch(name)]
		return wrong
	styled = COLOURED.fullmatch(prop) or "radius" in prop or "shadow" in prop
	if styled and re.search(r"var\(\s*--[\w-]+\s*,", value):
		wrong.append("a fallback: frappe-ui's tokens are always there")
	if prop in ("box-shadow", "text-shadow") and value != "none":
		wrong.append("a shadow")
	if prop in ("filter", "-webkit-filter", "backdrop-filter") and "drop-shadow" in value:
		wrong.append("a shadow")
	if COLOURED.fullmatch(prop):
		if LITERAL.search(value) or NAMED.search(re.sub(r"var\([^)]*\)", "", value)):
			wrong.append("a literal colour")
		wrong += [f"{name} is not a frappe-ui token" for name in _vars(value) if not TOKEN.fullmatch(name)]
	if re.fullmatch(rf"border{SIDE}", prop) and value not in ("none", "0", "inherit", "unset"):
		if not re.fullmatch(r"1px (solid|dashed) (var\(--[\w-]+\)|transparent|currentColor)", value):
			wrong.append("a border other than 1px of a token")
	if re.fullmatch(rf"border{SIDE}-width", prop) and not re.fullmatch(r"((0|1px)\s*)+", value):
		wrong.append("a border other than 1px")
	if re.fullmatch(r"border(-(top|bottom|start|end)-(left|right|start|end))?-radius", prop):
		if not all(RADIUS.fullmatch(part) or part in ("0", "inherit", "/") for part in value.split()):
			wrong.append("a radius that is not a --radius token")
	return wrong


def classes(text: str) -> list[str]:
	"""Tailwind classes that skip frappe-ui's tokens."""
	wrong = [
		f"{one} is the raw palette: use frappe-ui's ink, surface or outline" for one in PALETTE.findall(text)
	]
	wrong += [f"{one} is an arbitrary value" for one in ARBITRARY.findall(text)]
	wrong += [f"{one} is a border wider than 1px" for one in WIDE.findall(text)]
	for found in CLASSES.finditer(text):
		listed = " ".join(part or "" for part in found.groups())
		wrong += [f"{one} is a shadow" for one in SHADOW.findall(listed)]
	return wrong


def problems(path: Path, text: str) -> list[str]:
	out = []
	if str(path.relative_to(tree.ROOT)) in SANDBOXED:
		text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.S)
	for css in _css(path, text):
		for found in DECL.finditer(css):
			out += [
				f"{found.group(1)}: {found.group(2).strip()[:60]} ({why})"
				for why in declaration(*found.groups())
			]
	if path.suffix in (".vue", ".js", ".ts", ".html"):
		out += classes(text)
		out += [f"{one} is a literal colour" for one in QUOTED.findall(text)]
	return out


def test_every_screen_is_drawn_in_frappe_uis_tokens():
	found = {}
	for path in _screens():
		wrong = problems(path, path.read_text(encoding="utf-8", errors="ignore"))
		if wrong:
			found[str(path.relative_to(tree.ROOT))] = wrong
	assert not found, "\n".join(f"{path}:\n  " + "\n  ".join(wrong) for path, wrong in found.items())


def test_every_token_of_ours_is_defined():
	"""A `--one-*` colour is named, so it has to be defined somewhere of ours,
	or it falls through to nothing."""
	defined, used = set(), {}
	for path in _screens():
		text = path.read_text(encoding="utf-8", errors="ignore")
		defined |= set(re.findall(r"(--one-[\w-]+)\s*:", text))
		for name in re.findall(r"var\(\s*(--one-[\w-]+)", text):
			used.setdefault(name, str(path.relative_to(tree.ROOT)))
	assert not {name: where for name, where in used.items() if name not in defined}


def test_an_overlay_is_frappe_uis():
	wrong = []
	for path in _screens():
		for name, value in re.findall(
			r"--one-over-([\w-]+)\s*:\s*([^;]+);", path.read_text(encoding="utf-8", errors="ignore")
		):
			if OVER.get(name) != value.strip():
				wrong.append(f"{path.name}: --one-over-{name}: {value}")
	assert not wrong, wrong


def test_a_chart_is_coloured_by_frappe_uis_hues():
	"""frappe-charts paints SVG attributes, which take no var(), so a dashboard
	chart names one of frappe-ui's hues and chart_colors.js reads its token as
	it draws; a report's chart names frappe-charts' own. A report's cells are
	coloured by token, as a screen is."""
	hues = set(HUES.split("|")) | {"gray"}
	wrong = []
	for path in tree.APP.rglob("dashboard_chart/*/*.json"):
		options = json.loads(json.loads(path.read_text()).get("custom_options") or "{}")
		wrong += [
			f"{path.name}: {one}" for one in (options.get("one_colors") or {}).values() if one not in hues
		]
		wrong += [f"{path.name}: {one}" for one in options.get("colors") or []]
	for path in tree.APP.rglob("report/*/*.py"):
		text = path.read_text()
		wrong += [f"{path.name}: {one}" for one in LITERAL.findall(text)]
		wrong += [
			f"{path.name}: {one}" for one in re.findall(r"var\((--[\w-]+)", text) if not TOKEN.fullmatch(one)
		]
	assert not wrong, wrong


def test_the_scan_would_catch_each():
	for prop, value in (
		("color", "#fff"),
		("background", "var(--card-bg)"),
		("color", "var(--ink-gray-5, #999)"),
		("box-shadow", "var(--shadow-sm)"),
		("border", "2px solid var(--outline-gray-2)"),
		("border-radius", "8px"),
		("--one-x", "rgba(0, 0, 0, 0.1)"),
	):
		assert declaration(prop, value), (prop, value)
	for prop, value in (
		("color", "var(--ink-gray-5)"),
		("border", "1px solid var(--outline-gray-2)"),
		("border-radius", "var(--radius-full)"),
		("box-shadow", "none"),
		("--one-suite-1", "#38bdf8"),
	):
		assert not declaration(prop, value), (prop, value)
	assert classes('class="bg-gray-100 shadow-lg rounded-[6px] border-2"')
	assert not classes('class="bg-surface-gray-2 text-ink-gray-7 rounded-4 border shadow-none"')
