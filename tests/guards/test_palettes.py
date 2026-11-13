"""Palettes (onedesk/one_interface/AGENTS.md, Palettes): every rule of the frame
and the Canvas look reads a named role, and every palette sets every role,
so a palette is the whole of how One looks and a new part cannot slip
through on Standard's colours. These read the stylesheets."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CSS = ROOT / "onedesk" / "public" / "css" / "one_interface"
TOKENS = (CSS / "tokens.css").read_text(encoding="utf-8")
PALETTES = (CSS / "palettes.css").read_text(encoding="utf-8")

SCALE = re.compile(r"var\(--(?:(?:ink|surface|outline)-gray-\d+|gray-\d+|surface-base|ink-base|radius(?:-(?!full\b|none\b)[a-z0-9]+)?|font-stack|(?:shadow|elevation)-[a-z0-9]+)\)")
"""A step of frappe's scale, which only tokens.css and palettes.css may read."""
NOT_PALETTE = re.compile(r"^--one-(?:bar-|over-|layer-|frame$|frame-gutter$|check$)")
"""Not a palette's to set: layout, and names derived from the roles."""
SHAPE = re.compile(r"^--one-(?:radius-|heading-|button-weight$|font$)")


def blocks(text: str) -> list[tuple[str, str]]:
	return [(m.group(1).strip(), m.group(2)) for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", re.sub(r"/\*.*?\*/", "", text, flags=re.S))]


def declared(body: str) -> set[str]:
	return set(re.findall(r"(--[a-z0-9-]+)\s*:", body))


def _sheets() -> dict[str, str]:
	return {path.name: path.read_text(encoding="utf-8") for path in sorted(CSS.glob("*.css"))}


def roles(tokens: str = TOKENS) -> set[str]:
	found = set()
	for selector, body in blocks(tokens):
		if re.sub(r"\s+", " ", selector) in (":root", ":root, .one-sample"):
			found |= {name for name in declared(body) if name.startswith("--one-") and not NOT_PALETTE.match(name)}
	return found


def palettes(text: str = PALETTES) -> dict[str, dict[str, set[str]]]:
	found: dict[str, dict[str, set[str]]] = {}
	for selector, body in blocks(text):
		named = re.fullmatch(r':root(\[data-one-palette="([a-z]+)"\](\[data-theme="dark"\])?),\s*\.one-sample\1', selector)
		assert named, f"palettes.css: {selector} is not a palette's light or dark block, for the page and for a sample of it"
		found.setdefault(named.group(2), {}).setdefault("dark" if named.group(3) else "light", set()).update(declared(body))
	return found


def scale_reads(sheets: dict[str, str]) -> dict[str, list[str]]:
	"""The steps of frappe's scale each stylesheet but tokens.css and
	palettes.css reads. Pure."""
	read = {name: sorted(set(SCALE.findall(text))) for name, text in sheets.items() if name not in ("tokens.css", "palettes.css")}
	return {name: found for name, found in read.items() if found}


def test_no_interface_rule_reads_frappes_scale():
	read = scale_reads(_sheets())
	assert not read, f"read a role from tokens.css instead (or add one): {read}"


def undeclared(sheets: dict[str, str]) -> dict[str, list[str]]:
	"""The roles each stylesheet reads that none of them declares. Pure."""
	known = {name for text in sheets.values() for _selector, body in blocks(text) for name in declared(body)}
	missing = {name: sorted({role for role in re.findall(r"var\((--one-[a-z0-9-]+)", text) if role not in known}) for name, text in sheets.items()}
	return {name: unknown for name, unknown in missing.items() if unknown}


def test_every_role_read_is_declared():
	missing = undeclared(_sheets())
	assert not missing, missing


def palette_gaps(tokens: str, text: str) -> dict[str, list[str]]:
	"""The roles a palette's light block leaves unset, and the colours its
	dark block does. Pure."""
	everything = roles(tokens)
	colours = {name for name in everything if not SHAPE.match(name)}
	short = {}
	for name, themes in palettes(text).items():
		light, dark = themes.get("light", set()), themes.get("dark", set())
		if gap := sorted(everything - light):
			short[f"{name} light"] = gap
		if gap := sorted(colours - dark):
			short[f"{name} dark"] = gap
	return short


def test_every_palette_sets_every_role():
	assert palettes(), "palettes.css declares no palette"
	short = palette_gaps(TOKENS, PALETTES)
	assert not short, short


COPY_ROLES = {"--one-copy-band-bg", "--one-copy-band-ink", "--one-copy-vignette"}
"""What a training copy or a dev site draws in (chrome.js, copy_band)."""


def copy_unset(tokens: str, text: str) -> list[str]:
	"""The copy's roles tokens.css does not declare, or a palette leaves
	unset in its light or its dark. Pure."""
	missing = sorted(COPY_ROLES - roles(tokens))
	for name, themes in palettes(text).items():
		missing += [f"{name} {theme} {role}" for theme in ("light", "dark") for role in sorted(COPY_ROLES - themes.get(theme, set()))]
	return missing


def test_a_copy_is_drawn_in_every_palette():
	"""A copy never looks live, whatever the palette and theme: the band and
	the vignette are roles every palette sets for its light and its dark."""
	missing = copy_unset(TOKENS, PALETTES)
	assert not missing, missing


def stray(tokens: str, text: str) -> dict[str, list[str]]:
	"""What a palette sets that is neither a role nor a step of the gray
	scale. Pure."""
	allowed = roles(tokens) | {"--one-frame-ink", "--one-frame-ink-strong", "--one-frame-hover", "--one-frame-active", "--one-frame-line"}
	out = {}
	for name, themes in palettes(text).items():
		for theme, names in themes.items():
			extra = sorted(n for n in names if n not in allowed and not re.match(r"^--gray-\d+$", n))
			if extra:
				out[f"{name} {theme}"] = extra
	return out


def test_a_palette_sets_only_roles_and_the_scale():
	found = stray(TOKENS, PALETTES)
	assert not found, f"a palette sets a role or a step of the gray scale, nothing else: {found}"


def named_steps(text: str) -> list[tuple[str, str]]:
	"""A palette's roles written against frappe's named steps. Pure."""
	return re.findall(r"(--one-[a-z0-9-]+):\s*[^;]*var\(--((?:ink|surface|outline)-[a-z0-9-]+)\)", text)


def test_a_palette_writes_against_the_raw_scale():
	"""Under a palette frappe's named steps are the roles (tokens.css), so a
	role written as one of them would read itself."""
	named = named_steps(PALETTES)
	assert not named, f"write these against --gray-*, not a named step: {named}"


LEVELS = ("page", "island", "control", "float")
ON_LEVEL = {
	"canvas": "page",
	"sheet": "island",
	"card-bg": "island",
	"head-bg": "island",
	"head-button-bg": "control",
	"button-bg": "control",
	"menu-bg": "float",
	"dialog-bg": "float",
	"details-bg": "float",
	"status-bg": "float",
}
"""The four levels (onedesk/one_interface/AGENTS.md, Levels) and the surfaces
that stand on each. A surface not named here is a bridge to frappe's own
variables (--one-surface, --one-raised-bg, --one-control-bg,
--one-sidebar-bg) or a state or mark drawn on a level (hover, press, fill,
tint, chosen, count), not a level of its own."""


def palette_values(text: str = PALETTES) -> dict[str, dict[str, str]]:
	found: dict[str, dict[str, str]] = {}
	for selector, body in blocks(text):
		named = re.fullmatch(r':root(\[data-one-palette="([a-z]+)"\](\[data-theme="dark"\])?),\s*\.one-sample\1', selector)
		theme = f"{named.group(2)} {'dark' if named.group(3) else 'light'}"
		found.setdefault(theme, {}).update({k: v.strip() for k, v in re.findall(r"(--[a-z0-9-]+)\s*:\s*([^;]+);", body)})
	return found


def lightness(value: str, scale: dict[str, str]) -> float:
	"""How light a palette's value is, 0 to 1: an oklch() literal, a hex,
	or a step of the palette's own grey scale."""
	value = value.strip()
	if step := re.fullmatch(r"var\((--gray-\d+)\)", value):
		return lightness(scale[step.group(1)], scale)
	if lit := re.match(r"oklch\(\s*([\d.]+)", value):
		return float(lit.group(1))
	if hexa := re.fullmatch(r"#([0-9a-fA-F]{6})", value):
		r, g, b = (int(hexa.group(1)[i : i + 2], 16) / 255 for i in (0, 2, 4))
		return (0.2126 * r + 0.7152 * g + 0.0722 * b) ** (1 / 3)
	raise AssertionError(f"cannot read the lightness of {value}")


def off_level(tokens: str, text: str) -> dict[str, str]:
	"""The surfaces, in each palette and in tokens.css, that do not read
	their level. Pure."""
	wrong = {}
	for theme, values in palette_values(text).items():
		for role, level in ON_LEVEL.items():
			if values.get(f"--one-{role}") != f"var(--one-level-{level})":
				wrong[f"{theme} --one-{role}"] = f"should be var(--one-level-{level}), is {values.get(f'--one-{role}')}"
	said = {k: v.strip() for _s, body in blocks(tokens) for k, v in re.findall(r"(--one-[a-z0-9-]+)\s*:\s*([^;]+);", body)}
	for role, level in ON_LEVEL.items():
		if said.get(f"--one-{role}") != f"var(--one-level-{level})":
			wrong[f"tokens --one-{role}"] = f"should be var(--one-level-{level})"
	return wrong


def test_every_surface_stands_on_a_level():
	"""A surface reads its level, so a palette sets four values and every
	island, control and floating thing follows them."""
	wrong = off_level(TOKENS, PALETTES)
	assert not wrong, wrong


def out_of_order(text: str) -> dict[str, str]:
	"""Each palette whose levels do not stand apart in order. Pure."""
	out = {}
	for theme, values in palette_values(text).items():
		scale = {k: v for k, v in values.items() if re.fullmatch(r"--gray-\d+", k)}
		at = {level: lightness(values[f"--one-level-{level}"], scale) for level in LEVELS}
		rise = at["island"] - at["page"]
		if abs(rise) < 0.01:
			out[theme] = f"an island ({at['island']:.3f}) is the page ({at['page']:.3f})"
		elif abs(at["control"] - at["island"]) <= abs(rise):
			out[theme] = f"a control ({at['control']:.3f}) is nearer its island ({at['island']:.3f}) than the island is to the page"
		elif (at["float"] - at["page"]) * rise < 0 or abs(at["float"] - at["page"]) < abs(rise):
			out[theme] = f"what floats ({at['float']:.3f}) does not stand at least as far forward as an island"
	return out


def test_the_levels_keep_their_order():
	"""Each palette, light and dark: an island stands apart from the page; a
	control stands further from its island than the island from the page;
	and what floats is at least as far from the page as an island, on the
	same side. A dark palette may go darker as it comes forward."""
	out = out_of_order(PALETTES)
	assert not out, out


HEADS = {
	"list": r"\.frappe-list \.result > \.list-row-container:first-child::before \{ background: var\(--one-level-control\)",
	"record table": r"\.form-grid \.grid-heading-row \{ background: var\(--one-level-control\)",
	"report": r"\.dt-cell--header \.dt-cell__content\) \{ background-color: var\(--one-level-control\)",
}


def heads_off_control(canvas: str) -> list[str]:
	"""The column heads canvas.css does not put on the control level. Pure."""
	return [name for name, rule in HEADS.items() if not re.search(rule, canvas)]


def test_every_tables_column_heads_are_on_the_control_level():
	"""A list's, a record's table's and a report's column heads are one band,
	on the control level, the tone of the quick filters above them. Not the
	chosen state's fill: a head is not chosen."""
	missing = heads_off_control((CSS / "canvas.css").read_text(encoding="utf-8"))
	assert not missing, f"these column heads are not on the control level: {missing}"


def slate_problems(tokens: str) -> list[str]:
	"""How Slate's levels, set in tokens.css on frappe-ui's steps, fall out of
	order. Pure."""
	levels = {}
	for selector, body in blocks(tokens):
		if re.sub(r"\s+", " ", selector) in (":root", ":root, .one-sample"):
			levels.update(dict(re.findall(r"--one-level-(page|island|control|float):\s*var\(--surface-(base|gray-\d+)\)", body)))
	if set(levels) != set(LEVELS):
		return [f"Slate sets its levels on frappe-ui's steps: {levels}"]
	at = {k: 0 if v == "base" else int(v.split("-")[1]) for k, v in levels.items()}
	rise = at["island"] - at["page"]
	if not rise:
		return ["an island is the page"]
	out = []
	if abs(at["control"] - at["island"]) <= abs(rise):
		out.append(f"a control is nearer its island than the island is to the page: {levels}")
	if not ((at["float"] - at["page"]) * rise >= 0 and abs(at["float"] - at["page"]) >= abs(rise)):
		out.append(f"what floats is behind an island: {levels}")
	return out


def test_slates_levels_keep_their_order():
	"""Slate (id standard) is tokens.css's own roles on frappe-ui's steps.
	frappe-ui's surface-gray-N moves away from surface-base as N grows, in
	light and in dark alike, so a level's distance from base is its N."""
	found = slate_problems(TOKENS)
	assert not found, found


SELECTED = re.compile(r'\.is-on\b|\.active\b|\.active-sidebar\b|aria-selected="true"|aria-pressed="true"|data-state="(?:active|on)"')
CHOOSING = ("canvas.css", "views.css", "dialogs.css", "phone.css", "centre.css")


def unchosen(name: str, text: str) -> list[str]:
	"""The chosen things in a stylesheet filled with anything but
	--one-chosen (or nothing). Pure."""
	wrong = []
	for selector, body in blocks(text):
		fill = re.search(r"(?<![-\w])background(?:-color)?\s*:\s*([^;]+)", body)
		if not fill or ":hover" in selector or "::" in selector:
			continue
		for part in selector.split(","):
			tail = re.split(r"\s+", part.strip())[-1]
			if SELECTED.search(tail) and "var(--one-chosen)" not in fill.group(1) and "transparent" not in fill.group(1):
				wrong.append(f"{name}: {part.strip()[-90:]} -> {fill.group(1).strip()}")
	return wrong


def test_every_selected_thing_is_one_fill():
	"""A chosen tab, a chosen state in the strip, a chosen way of looking, the
	sidebar's row, a panel's tab, a pressed switch: one fill, --one-chosen,
	so being chosen reads the same wherever it is. A mark drawn inside the
	chosen thing (a count, an underline) is not its fill. Canvas's sheets
	only, and the kit's dialogs, the phone's sheets and Help, which every look
	shows: frame.css is the Standard look's own, and chrome.css chooses on the
	dark frame's bars, a ground of its own."""
	wrong = [line for name in CHOOSING for line in unchosen(name, (CSS / name).read_text(encoding="utf-8"))]
	assert not wrong, "a chosen thing's fill is --one-chosen:\n" + "\n".join(wrong)


ISLANDS = {
	"record section": r"\.form-section:not\(\.empty-section\) \{[^}]*background: var\(--one-sheet\)[^}]*border: 1px solid var\(--one-line\)[^}]*border-radius: var\(--one-radius-sheet\)",
	"list": r"\.frappe-list \.result-container \{[^}]*background: var\(--one-level-island\)[^}]*border: 1px solid var\(--one-line\)[^}]*border-radius: var\(--one-radius-sheet\)",
	"report": r"\.datatable \{[^}]*border: 1px solid var\(--one-line\)[^}]*border-radius: var\(--one-radius-sheet\)",
}


def misshapen(canvas: str) -> list[str]:
	"""The islands canvas.css no longer draws in the island's shape. Pure."""
	return [name for name, rule in ISLANDS.items() if not re.search(rule, canvas)]


def test_every_island_is_one_shape():
	"""A record's section card, a list and a report's table are one island:
	the island level, the sheet radius, a hairline of --one-line."""
	missing = misshapen((CSS / "canvas.css").read_text(encoding="utf-8"))
	assert not missing, f"these islands lost the island's shape: {missing}"


def _palette(name: str, light: str, dark: str) -> str:
	return "".join(
		f':root[data-one-palette="{name}"]{theme},\n.one-sample[data-one-palette="{name}"]{theme} {{\n{body}\n}}\n'
		for theme, body in (("", light), ('[data-theme="dark"]', dark))
	)


def test_the_palette_rules_catch_their_examples():
	assert scale_reads({"frame.css": "a { color: var(--ink-gray-7); }", "tokens.css": "a { color: var(--ink-gray-7); }", "b.css": "a { color: var(--one-ink); }"}) == {
		"frame.css": ["var(--ink-gray-7)"]
	}
	assert undeclared({"a.css": ":root { --one-ink: red; }", "b.css": "a { color: var(--one-ink); background: var(--one-lost); }"}) == {"b.css": ["--one-lost"]}
	tokens = ":root { --one-ink: var(--ink-gray-8); --one-radius-sheet: 8px; --one-bar-height: 40px; }"
	assert roles(tokens) == {"--one-ink", "--one-radius-sheet"}
	whole = _palette("sand", "--one-ink: var(--gray-9); --one-radius-sheet: 6px;", "--one-ink: var(--gray-1);")
	assert not palette_gaps(tokens, whole)
	assert palette_gaps(tokens, _palette("sand", "--one-ink: var(--gray-9);", "")) == {"sand light": ["--one-radius-sheet"], "sand dark": ["--one-ink"]}
	assert not stray(tokens, whole)
	copied = ":root { " + "".join(f"{role}: red; " for role in sorted(COPY_ROLES)) + "}"
	every = "".join(f"{role}: red; " for role in sorted(COPY_ROLES))
	assert not copy_unset(copied, _palette("sand", every, every))
	assert copy_unset(copied, _palette("sand", every, "--one-copy-band-bg: red;")) == ["sand dark --one-copy-band-ink", "sand dark --one-copy-vignette"]
	assert copy_unset(":root { }", "") == sorted(COPY_ROLES)
	assert stray(tokens, _palette("sand", "--one-ink: red; --one-own: red; --gray-1: #fff;", "")) == {"sand light": ["--one-own"]}
	assert named_steps("--one-ink: var(--ink-gray-8); --one-line: var(--gray-3);") == [("--one-ink", "ink-gray-8")]
	on = "".join(f"--one-{role}: var(--one-level-{level}); " for role, level in ON_LEVEL.items())
	levels = "--one-level-page: oklch(0.95 0 0); --one-level-island: oklch(0.97 0 0); --one-level-control: oklch(0.93 0 0); --one-level-float: oklch(0.99 0 0); "
	assert not off_level(f":root {{ {on} }}", _palette("sand", levels + on, levels + on))
	assert off_level(f":root {{ {on} }}", _palette("sand", levels + on.replace("var(--one-level-float); ", "#fff; ", 1), levels + on)) == {
		"sand light --one-menu-bg": "should be var(--one-level-float), is #fff"
	}
	assert not out_of_order(_palette("sand", levels, levels))
	flat = levels.replace("0.97", "0.95")
	near = levels.replace("0.93", "0.96")
	behind = levels.replace("0.99", "0.90")
	assert set(out_of_order(_palette("sand", flat, near))) == {"sand light", "sand dark"}
	assert out_of_order(_palette("sand", behind, levels)) == {"sand light": "what floats (0.900) does not stand at least as far forward as an island"}
	assert lightness("var(--gray-1)", {"--gray-1": "#ffffff"}) == 1.0
	assert heads_off_control("") == list(HEADS)
	assert not heads_off_control(
		".frappe-list .result > .list-row-container:first-child::before { background: var(--one-level-control) }"
		".form-grid .grid-heading-row { background: var(--one-level-control) }"
		":is(.dt-cell--header .dt-cell__content) { background-color: var(--one-level-control) }"
	)
	slate = ":root { --one-level-page: var(--surface-gray-1); --one-level-island: var(--surface-base); --one-level-control: var(--surface-gray-3); --one-level-float: var(--surface-base); }"
	assert not slate_problems(slate)
	assert slate_problems(slate.replace("gray-3", "gray-1")) == [
		"a control is nearer its island than the island is to the page: {'page': 'gray-1', 'island': 'base', 'control': 'gray-1', 'float': 'base'}"
	]
	assert slate_problems(":root { --one-level-page: var(--surface-base); }")[0].startswith("Slate sets its levels")
	assert unchosen("a.css", ".tab.active, .tab { background: var(--one-level-control); }\n.tab.active:hover { background: red; }\n.row.is-on { background: var(--one-chosen); }") == [
		"a.css: .tab.active -> var(--one-level-control)"
	]
	assert misshapen("") == list(ISLANDS)
	assert misshapen(".datatable { border: 1px solid var(--one-line); border-radius: var(--one-radius-sheet); }") == ["record section", "list"]
