"""OneAI is a rail of its own (docs/ONE.md, stage 6): Documents, the
conversations, suggestions and knowledge, its reports and AICenter, which
were One's OneAI group. What the operator does lives in OneAdmin.
"""

import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import tree

HOOKS = tree.APP / "hooks.py"
ONE = tree.APP / "one" / "sidebar" / "one" / "one.json"
RAIL = tree.APP / "one_ai" / "sidebar" / "oneai" / "oneai.json"
DOCK = tree.APP / "dock" / "onedesk" / "onedesk.json"
ADMIN = tree.APP / "one_admin" / "sidebar" / "one_admin" / "one_admin.json"
CREDITS = tree.APP / "one_ai" / "report" / "ai_credits"
PROXY = tree.APP / "one_admin" / "proxy.py"


def _hook(name: str):
	for node in ast.parse(HOOKS.read_text(encoding="utf-8")).body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", None) == name:
			return ast.literal_eval(node.value)
	return None


def _links(path: Path) -> set[str]:
	return {i.get("link_to") for i in json.loads(path.read_text())["items"] if i.get("type") == "Link"}


def test_one_ai_is_on_the_dock_with_a_rail_of_its_own():
	"""Its records open in its own rail, so it is no code-only module."""
	assert "One AI" not in _hook("code_only_modules")
	assert "OneAI" in {one["link_to"] for one in json.loads(DOCK.read_text())["items"]}
	assert json.loads(RAIL.read_text())["module"] == "One AI"


def test_what_a_workspace_administers_of_it_is_in_its_rail_not_ones():
	held = {"AI Credits", "AI Chat", "AI Proposal", "AI Knowledge", "intake"}
	assert held <= _links(RAIL) and not held & _links(ONE)
	urls = {i.get("url") for i in json.loads(RAIL.read_text())["items"] if i.get("type") == "Link"}
	assert "/desk/one?center=ai" in urls, "AICenter is not on OneAI's rail"
	# One's rail has AICenter only as one of its Centers (docs/READY.md,
	# mechanism 18), never OneAI's own screens.
	items = json.loads(ONE.read_text())["items"]
	labels = [i.get("label") for i in items]
	assert "OneAI" not in labels
	assert labels.index("AICenter") > labels.index("Centers")


def test_what_the_operator_does_is_in_one_admin():
	assert "AI Usage" in _links(ADMIN) and "AI Model" not in _links(ADMIN)


def test_a_workspaces_credits_are_its_administrators_and_its_own():
	report = json.loads((CREDITS / "ai_credits.json").read_text())
	assert [r["role"] for r in report["roles"]] == ["Workspace Administrator"]
	assert "roles.require()" in (CREDITS / "ai_credits.py").read_text()
	proxy = PROXY.read_text()
	said = proxy[proxy.index("def ai_usage("):]
	said = said[: said.index("\n@frappe.whitelist")]
	assert "caller()" in said, "a workspace could ask for another's usage"
	assert "tenant=" not in said.split("caller()")[0], "the tenant comes from the token, not the body"


def test_a_settings_page_is_a_record_and_no_field_carries_a_mark():
	"""A Single's route has no name, so it was read as a list. No field, mail
	window or page field carries a OneAI button: the field the reader was in
	when they opened the panel is what it writes, or what the question is
	about, and an open mail window is what it writes in."""
	js = (tree.APP / "public" / "js" / "one_ai" / "oneai.js").read_text()
	assert "single ? route[1]" in js
	fields = js[js.index("onedesk.oneai.fields = function"):js.index("onedesk.oneai.made = function")]
	assert "<button" not in fields and "one-ai-help" not in js, "a button beside a field's label"
	assert "this.justLeft()" in js and "JUST_LEFT_MS" in js
	assert "one-ai-write" not in js and "await this.inMail()" in js, "a OneAI button in the mail window"
	edit = (tree.ROOT / "frontend" / "src" / "kit" / "FieldEdit.vue").read_text()
	assert "<button\n        v-if=\"writable && long" not in edit and "aiLeft(" in edit, "a OneAI button beside a page's field"
	suggest = (tree.APP / "one_ai" / "suggest.py").read_text()
	assert "issingle" in suggest and "Help me set this up" in suggest
	panel = (tree.APP / "public" / "js" / "one_ai" / "panel" / "Panel.vue").read_text()
	assert "opening && opening.ask" in panel and "opening && opening.about" in panel


def test_no_oneai_button_on_a_page():
	"""Everything OneAI does is offered in its panel, for the page it opens on.

	A form carrying an AI button per feature is a form nobody reads, and a
	person looking for help looks in one place. A suggestion with `run` covers
	the things that are a job rather than a question; see one_ai/suggest.py.
	"""
	import re

	found = []
	for path in sorted((tree.APP / "public" / "js").rglob("*.js")):
		text = path.read_text(encoding="utf-8")
		for call in re.finditer(r"add_custom_button\((.{0,400}?)\);", text, re.S):
			if re.search(r"__\(\"OneAI\"\)|onedesk\.one_ai|one_hr\.hiring\.|oneai\.", call.group(1)):
				found.append(f"{path.relative_to(tree.APP)}: {call.group(1)[:80]!r}")
	assert not found, "offer these in the OneAI panel instead:\n" + "\n".join(found)
