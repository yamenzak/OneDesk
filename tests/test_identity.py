"""The workspace's own name, logo and colour (one_interface/identity.py): one
setting in One's ControlCenter › Branding, kept in frappe's own fields, that
the top bar, the sign-in page, the tab, the installed app, mails and the
accent of every look and palette read. Pure parts, and what reads them."""

import ast
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

IDENTITY = tree.APP / "one_interface" / "identity.py"
HEADS = tree.APP / "one_studio" / "letter_heads.py"
CSS = tree.APP / "public" / "css" / "one_interface"


def _load(path, names, **space):
	for node in ast.parse(path.read_text()).body:
		named = getattr(node, "name", None) or (getattr(node.targets[0], "id", None) if isinstance(node, ast.Assign) else None)
		if named in names:
			exec(ast.unparse(node), space)
	return space


class _Heads:
	pass


for _name, _value in _load(HEADS, {"INK", "_rgb", "_luminance", "_contrast", "readable", "on"}).items():
	setattr(_Heads, _name, staticmethod(_value) if callable(_value) else _value)

I = _load(IDENTITY, {"HEX", "DARK_PAGE", "shades", "lifted", "_apart"}, re=re, letter_heads=_Heads)


def _luminance(colour):
	return _Heads._luminance(_Heads._rgb(colour))


def test_every_shade_reads_where_it_stands():
	for colour in ("#0E6E8C", "#FFD400", "#111111", "#7C2D12", "#F5F5F5", "#2563EB"):
		said = I["shades"](colour)
		assert said["colour"] == colour
		assert I["_apart"](_Heads._rgb(said["ink"]), _Heads._rgb(colour)) >= 3, (colour, said)
		assert I["_apart"](_Heads._rgb(said["accent"]), (255, 255, 255)) >= 4.5, (colour, said)
		assert I["_apart"](_Heads._rgb(said["dark"]), I["DARK_PAGE"]) >= 4.5, (colour, said)
		assert I["_apart"](_Heads._rgb(said["dark_ink"]), _Heads._rgb(said["dark"])) >= 4.5, (colour, said)


def test_a_light_colour_is_kept_and_a_dark_one_lifted():
	assert I["lifted"]("#F5F5F5") == "#f5f5f5"
	assert _luminance(I["lifted"]("#0E6E8C")) > _luminance("#0E6E8C")


def test_no_colour_is_ones_own():
	assert I["shades"](None) is None and I["shades"]("") is None and I["shades"]("teal") is None


def test_the_colour_outweighs_every_palette_in_both_themes():
	"""A palette's block is `:root[data-one-palette=…]` (with
	`[data-theme="dark"]`); the workspace's colour is read under selectors
	one attribute heavier, light first and dark after it, so in any palette
	and theme the main button, the accent and the focus are its shades."""
	tokens = (CSS / "tokens.css").read_text(encoding="utf-8")
	light = tokens.index(":root[data-one-brand][data-theme][data-one-palette],")
	dark = tokens.index(':root[data-one-brand][data-theme="dark"][data-one-palette],')
	assert light < dark
	for role in ("--one-primary-bg", "--one-primary-ink", "--one-accent", "--one-focus"):
		assert role in tokens[light:dark] and role in tokens[dark:], role
	assert "--one-brand" not in (CSS / "palettes.css").read_text(encoding="utf-8")


def test_one_setting_reaches_the_shell_the_mail_and_frappes_fields():
	chrome = (tree.APP / "public" / "js" / "one_interface" / "chrome.js").read_text(encoding="utf-8")
	assert "root.dataset.oneBrand" in chrome and '"one_brand"' in chrome and "one-bar-logo" in chrome
	assert "onedesk.one_interface.identity.manifest" in chrome and 'link[rel~="icon"]' in chrome
	assert 'bootinfo["one_brand"] = identity.boot()' in (tree.APP / "one" / "boot.py").read_text()
	control = (tree.APP / "one" / "control.py").read_text()
	assert '"app_name", "app_logo"' in control and "identity.save(values)" in control and "system.app_name" in control
	assert "identity.name() or workspace()" in (tree.APP / "one" / "notify.py").read_text()
	source = IDENTITY.read_text()
	for field in ('"Website Settings", "app_name"', '"Website Settings", "app_logo"', '"Navbar Settings": ("app_logo",)', '"favicon", "splash_image"'):
		assert field in source, field
