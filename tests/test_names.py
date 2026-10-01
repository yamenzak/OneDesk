"""A product's name is one word, and the "One" of it is light. docs/WORDING.md."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

LOCALE = tree.APP / "locale"
SPACED = re.compile(
	r"\bOne (AI|Admin|Book|Calendar|Cloud|CRM|HR|Intake|Inventory|Legal|Mail|Project|Task|Writer|Workbook|Desk|Studio)\b"
)
ENTRY = re.compile(r'^msgid "(.*)"\nmsgstr "(.*)"', re.M)


def _catalogue(name: str) -> dict:
	return dict(ENTRY.findall((LOCALE / name).read_text(encoding="utf-8")))


def test_nothing_on_screen_spaces_a_products_name():
	english = _catalogue("en.po")
	for msgid in _catalogue("main.pot"):
		if SPACED.search(msgid):
			# An id, named in English as the product.
			assert msgid in english, f"{msgid!r} spaces a product's name; write it as one word"


def test_every_module_id_has_its_products_name():
	english = _catalogue("en.po")
	for module in (tree.APP / "modules.txt").read_text(encoding="utf-8").split("\n"):
		if module.startswith("One "):
			assert module in english, f"en.po does not say what {module} is called"
			assert " " not in english[module], english[module]
	for lang in ("ar", "de"):
		for msgid, msgstr in _catalogue(f"{lang}.po").items():
			assert not SPACED.search(msgstr), f"{lang}: {msgid!r} is translated with a spaced name"


def test_the_one_of_a_name_is_light_everywhere():
	hooks = (tree.APP / "hooks.py").read_text(encoding="utf-8")
	assert '"/assets/onedesk/js/brand.js"' in hooks
	brand = (tree.APP / "public" / "js" / "brand.js").read_text(encoding="utf-8")
	assert "MutationObserver" in brand and '"one-light"' in brand and '"one-name"' in brand
	# What a person types, and what a Vue app keeps, is left alone.
	for kept in ("input", "textarea", "[contenteditable]", "[data-v-app]"):
		assert kept in brand
	assert ".one-light {" in (tree.APP / "public" / "css" / "desk.css").read_text(encoding="utf-8")
