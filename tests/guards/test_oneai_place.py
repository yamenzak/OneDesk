"""OneAI is not a place on the rail.

What a workspace administers of it lives in One; what the operator does lives in
OneAdmin. A module sidebar of its own was five doctype lists nobody navigated
to, and it would come back the day somebody added a doctype to the module —
which is what `code_only_modules` stops.
"""

import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import tree

HOOKS = tree.APP / "hooks.py"
ONE = tree.APP / "one" / "sidebar" / "one" / "one.json"
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


def test_one_ai_has_no_dock_entry_and_one_inherits_it():
	"""A mapping, as frappe's and erpnext's are: a list here breaks every request."""
	assert _hook("code_only_modules")["One AI"] == ["One"]


def test_what_a_workspace_administers_is_in_one():
	assert {"settings", "AI Credits", "AI Chat", "AI Proposal"} <= _links(ONE)
	assert '"oneai": _oneai' in (tree.APP / "one" / "settings.py").read_text()


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
	js = (tree.APP / "public" / "js" / "oneai.js").read_text()
	assert "single ? route[1]" in js
	fields = js[js.index("onedesk.oneai.fields = function"):js.index("onedesk.oneai.made = function")]
	assert "<button" not in fields and "one-ai-help" not in js, "a button beside a field's label"
	assert "this.justLeft()" in js and "JUST_LEFT_MS" in js
	assert "one-ai-write" not in js and "await this.inMail()" in js, "a OneAI button in the mail window"
	edit = (tree.ROOT / "frontend" / "src" / "kit" / "FieldEdit.vue").read_text()
	assert "<button\n        v-if=\"writable && long" not in edit and "aiLeft(" in edit, "a OneAI button beside a page's field"
	suggest = (tree.APP / "one_ai" / "suggest.py").read_text()
	assert "issingle" in suggest and "Help me set this up" in suggest
	panel = (tree.APP / "public" / "js" / "oneai" / "Panel.vue").read_text()
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
