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
NOT_PALETTE = re.compile(r"^--one-(?:bar-|over-|frame$|frame-gutter$|check$)")
SHAPE = re.compile(r"^--one-(?:radius-|heading-|button-weight$|font$)")


def blocks(text: str) -> list[tuple[str, str]]:
	return [(m.group(1).strip(), m.group(2)) for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", re.sub(r"/\*.*?\*/", "", text, flags=re.S))]


def declared(body: str) -> set[str]:
	return set(re.findall(r"(--[a-z0-9-]+)\s*:", body))


def roles() -> set[str]:
	found = set()
	for selector, body in blocks(TOKENS):
		if selector == ":root":
			found |= {name for name in declared(body) if name.startswith("--one-") and not NOT_PALETTE.match(name)}
	return found


def palettes() -> dict[str, dict[str, set[str]]]:
	found: dict[str, dict[str, set[str]]] = {}
	for selector, body in blocks(PALETTES):
		named = re.fullmatch(r':root\[data-one-palette="([a-z]+)"\](\[data-theme="dark"\])?', selector)
		assert named, f"palettes.css: {selector} is not a palette's light or dark block"
		found.setdefault(named.group(1), {}).setdefault("dark" if named.group(2) else "light", set()).update(declared(body))
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
