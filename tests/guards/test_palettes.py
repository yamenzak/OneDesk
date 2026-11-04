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

# A step of frappe's scale, which only tokens.css and palettes.css may read.
SCALE = re.compile(r"var\(--(?:(?:ink|surface|outline)-gray-\d+|gray-\d+|surface-base|ink-base|radius(?:-(?!full\b|none\b)[a-z0-9]+)?|font-stack|(?:shadow|elevation)-[a-z0-9]+)\)")
# Not a palette's to set: layout, and names derived from the roles.
NOT_PALETTE = re.compile(r"^--one-(?:bar-|over-|layer-|frame$|frame-gutter$|check$)")
SHAPE = re.compile(r"^--one-(?:radius-|heading-|button-weight$|font$)")


def blocks(text: str) -> list[tuple[str, str]]:
	return [(m.group(1).strip(), m.group(2)) for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", re.sub(r"/\*.*?\*/", "", text, flags=re.S))]


def declared(body: str) -> set[str]:
	return set(re.findall(r"(--[a-z0-9-]+)\s*:", body))


def roles() -> set[str]:
	found = set()
	for selector, body in blocks(TOKENS):
		if re.sub(r"\s+", " ", selector) in (":root", ":root, .one-sample"):
			found |= {name for name in declared(body) if name.startswith("--one-") and not NOT_PALETTE.match(name)}
	return found


def palettes() -> dict[str, dict[str, set[str]]]:
	found: dict[str, dict[str, set[str]]] = {}
	for selector, body in blocks(PALETTES):
		named = re.fullmatch(r':root(\[data-one-palette="([a-z]+)"\](\[data-theme="dark"\])?),\s*\.one-sample\1', selector)
		assert named, f"palettes.css: {selector} is not a palette's light or dark block, for the page and for a sample of it"
		found.setdefault(named.group(2), {}).setdefault("dark" if named.group(3) else "light", set()).update(declared(body))
	return found


def test_no_interface_rule_reads_frappes_scale():
	read = {
		path.name: sorted(set(SCALE.findall(path.read_text(encoding="utf-8"))))
		for path in sorted(CSS.glob("*.css"))
		if path.name not in ("tokens.css", "palettes.css")
	}
	read = {name: found for name, found in read.items() if found}
	assert not read, f"read a role from tokens.css instead (or add one): {read}"


def test_every_role_read_is_declared():
	known = set()
	for path in CSS.glob("*.css"):
		for _selector, body in blocks(path.read_text(encoding="utf-8")):
			known |= declared(body)
	missing = {}
	for path in sorted(CSS.glob("*.css")):
		unknown = sorted({name for name in re.findall(r"var\((--one-[a-z0-9-]+)", path.read_text(encoding="utf-8")) if name not in known})
		if unknown:
			missing[path.name] = unknown
	assert not missing, missing


def test_every_palette_sets_every_role():
	everything = roles()
	colours = {name for name in everything if not SHAPE.match(name)}
	found = palettes()
	assert found, "palettes.css declares no palette"
	short = {}
	for name, themes in found.items():
		light, dark = themes.get("light", set()), themes.get("dark", set())
		if gap := sorted(everything - light):
			short[f"{name} light"] = gap
		if gap := sorted(colours - dark):
			short[f"{name} dark"] = gap
	assert not short, short


def test_a_palette_sets_only_roles_and_the_scale():
	allowed = roles() | {"--one-frame-ink", "--one-frame-ink-strong", "--one-frame-hover", "--one-frame-active", "--one-frame-line"}
	stray = {}
	for name, themes in palettes().items():
		for theme, names in themes.items():
			extra = sorted(n for n in names if n not in allowed and not re.match(r"^--gray-\d+$", n))
			if extra:
				stray[f"{name} {theme}"] = extra
	assert not stray, f"a palette sets a role or a step of the gray scale, nothing else: {stray}"


def test_a_palette_writes_against_the_raw_scale():
	"""Under a palette frappe's named steps are the roles (tokens.css), so a
	role written as one of them would read itself."""
	named = re.findall(r"(--one-[a-z0-9-]+):\s*[^;]*var\(--((?:ink|surface|outline)-[a-z0-9-]+)\)", PALETTES)
	assert not named, f"write these against --gray-*, not a named step: {named}"


# The four levels (onedesk/one_interface/AGENTS.md, Levels) and the surfaces
# that stand on each. A surface not named here is a bridge to frappe's own
# variables (--one-surface, --one-raised-bg, --one-control-bg,
# --one-sidebar-bg) or a state or mark drawn on a level (hover, press,
# fill, tint, chosen, count), not a level of its own.
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


def palette_values() -> dict[str, dict[str, str]]:
	found: dict[str, dict[str, str]] = {}
	for selector, body in blocks(PALETTES):
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


def test_every_surface_stands_on_a_level():
	"""A surface reads its level, so a palette sets four values and every
	island, control and floating thing follows them."""
	wrong = {}
	for theme, values in palette_values().items():
		for role, level in ON_LEVEL.items():
			if values.get(f"--one-{role}") != f"var(--one-level-{level})":
				wrong[f"{theme} --one-{role}"] = f"should be var(--one-level-{level}), is {values.get(f'--one-{role}')}"
	tokens = {k: v.strip() for _s, body in blocks(TOKENS) for k, v in re.findall(r"(--one-[a-z0-9-]+)\s*:\s*([^;]+);", body)}
	for role, level in ON_LEVEL.items():
		if tokens.get(f"--one-{role}") != f"var(--one-level-{level})":
			wrong[f"tokens --one-{role}"] = f"should be var(--one-level-{level})"
	assert not wrong, wrong


def test_the_levels_keep_their_order():
	"""Each palette, light and dark: an island stands apart from the page; a
	control stands further from its island than the island from the page;
	and what floats is at least as far from the page as an island, on the
	same side. A dark palette may go darker as it comes forward."""
	out = {}
	for theme, values in palette_values().items():
		scale = {k: v for k, v in values.items() if re.fullmatch(r"--gray-\d+", k)}
		at = {level: lightness(values[f"--one-level-{level}"], scale) for level in LEVELS}
		rise = at["island"] - at["page"]
		if abs(rise) < 0.01:
			out[theme] = f"an island ({at['island']:.3f}) is the page ({at['page']:.3f})"
		elif abs(at["control"] - at["island"]) <= abs(rise):
			out[theme] = f"a control ({at['control']:.3f}) is nearer its island ({at['island']:.3f}) than the island is to the page"
		elif (at["float"] - at["page"]) * rise < 0 or abs(at["float"] - at["page"]) < abs(rise):
			out[theme] = f"what floats ({at['float']:.3f}) does not stand at least as far forward as an island"
	assert not out, out


def test_every_tables_column_heads_are_on_the_control_level():
	"""A list's, a record's table's and a report's column heads are one band,
	on the control level, the tone of the quick filters above them. Not the
	chosen state's fill: a head is not chosen."""
	canvas = (CSS / "canvas.css").read_text(encoding="utf-8")
	heads = {
		"list": r"\.frappe-list \.result > \.list-row-container:first-child::before \{ background: var\(--one-level-control\)",
		"record table": r"\.form-grid \.grid-heading-row \{ background: var\(--one-level-control\)",
		"report": r"\.dt-cell--header \.dt-cell__content\) \{ background-color: var\(--one-level-control\)",
	}
	missing = [name for name, rule in heads.items() if not re.search(rule, canvas)]
	assert not missing, f"these column heads are not on the control level: {missing}"


def test_slates_levels_keep_their_order():
	"""Slate (id standard) is tokens.css's own roles on frappe-ui's steps.
	frappe-ui's surface-gray-N moves away from surface-base as N grows, in
	light and in dark alike, so a level's distance from base is its N."""
	levels = {}
	for selector, body in blocks(TOKENS):
		if re.sub(r"\s+", " ", selector) in (":root", ":root, .one-sample"):
			levels.update(dict(re.findall(r"--one-level-(page|island|control|float):\s*var\(--surface-(base|gray-\d+)\)", body)))
	assert set(levels) == set(LEVELS), f"Slate sets its levels on frappe-ui's steps: {levels}"
	at = {k: 0 if v == "base" else int(v.split("-")[1]) for k, v in levels.items()}
	rise = at["island"] - at["page"]
	assert rise, "an island is the page"
	assert abs(at["control"] - at["island"]) > abs(rise), f"a control is nearer its island than the island is to the page: {levels}"
	assert (at["float"] - at["page"]) * rise >= 0 and abs(at["float"] - at["page"]) >= abs(rise), f"what floats is behind an island: {levels}"


SELECTED = re.compile(r'\.is-on\b|\.active\b|\.active-sidebar\b|aria-selected="true"|aria-pressed="true"|data-state="(?:active|on)"')


def test_every_selected_thing_is_one_fill():
	"""A chosen tab, a chosen state in the strip, a chosen way of looking, the
	sidebar's row, a panel's tab, a pressed switch: one fill, --one-chosen,
	so being chosen reads the same wherever it is. A mark drawn inside the
	chosen thing (a count, an underline) is not its fill. Canvas's sheets
	only, and the kit's dialogs, the phone's sheets and Help, which every look
	shows: frame.css is the Standard look's own, and chrome.css chooses on the
	dark frame's bars, a ground of its own."""
	wrong = []
	for name in ("canvas.css", "views.css", "dialogs.css", "phone.css", "../module_docs.css"):
		for selector, body in blocks((CSS / name).read_text(encoding="utf-8")):
			fill = re.search(r"(?<![-\w])background(?:-color)?\s*:\s*([^;]+)", body)
			if not fill or ":hover" in selector or "::" in selector:
				continue
			for part in selector.split(","):
				tail = re.split(r"\s+", part.strip())[-1]
				if SELECTED.search(tail) and "var(--one-chosen)" not in fill.group(1) and "transparent" not in fill.group(1):
					wrong.append(f"{name}: {part.strip()[-90:]} -> {fill.group(1).strip()}")
	assert not wrong, "a chosen thing's fill is --one-chosen:\n" + "\n".join(wrong)


def test_every_island_is_one_shape():
	"""A record's section card, a list and a report's table are one island:
	the island level, the sheet radius, a hairline of --one-line."""
	canvas = (CSS / "canvas.css").read_text(encoding="utf-8")
	islands = {
		"record section": r"\.form-section:not\(\.empty-section\) \{[^}]*background: var\(--one-sheet\)[^}]*border: 1px solid var\(--one-line\)[^}]*border-radius: var\(--one-radius-sheet\)",
		"list": r"\.frappe-list \.result-container \{[^}]*background: var\(--one-level-island\)[^}]*border: 1px solid var\(--one-line\)[^}]*border-radius: var\(--one-radius-sheet\)",
		"report": r"\.datatable \{[^}]*border: 1px solid var\(--one-line\)[^}]*border-radius: var\(--one-radius-sheet\)",
	}
	missing = [name for name, rule in islands.items() if not re.search(rule, canvas)]
	assert not missing, f"these islands lost the island's shape: {missing}"
