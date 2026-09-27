"""What is AI is drawn one way: onedesk.oneai.tag and onedesk.oneai.button
(public/js/oneai.js, oneai.css). docs/PASSOVER.md, point 2."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

JS = tree.APP / "public" / "js"


def test_the_tag_and_the_button_are_frappes_own_in_oneais_colours():
	oneai = (JS / "oneai.js").read_text(encoding="utf-8")
	assert "onedesk.oneai.tag = " in oneai and "frappe.ui.badge.html(" in oneai
	assert "onedesk.oneai.button = " in oneai and "frappe.ui.button.html(" in oneai
	assert '"[data-one-ai-ask]"' in oneai, "a button asks its question wherever it is drawn"
	css = (tree.APP / "public" / "css" / "oneai.css").read_text(encoding="utf-8")
	for part in (".es-badge.one-ai-tag", ".es-button.one-ai-button"):
		assert part in css
	assert "var(--one-ai-spectrum) border-box" in css


def test_nothing_badges_oneai_by_hand():
	for path in sorted(JS.rglob("*.js")):
		source = path.read_text(encoding="utf-8")
		for badge in re.findall(r"frappe\.ui\.badge\.html\(\{[^}]*\}", source):
			assert "OneAI" not in badge, f"{path.name}: use onedesk.oneai.tag for {badge}"
