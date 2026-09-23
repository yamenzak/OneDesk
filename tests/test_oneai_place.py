"""OneAI is not a place on the rail.

What a workspace administers of it lives in One; what the operator does lives in
One Admin. A module sidebar of its own was five doctype lists nobody navigated
to, and it would come back the day somebody added a doctype to the module —
which is what `code_only_modules` stops.
"""

import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

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
	assert _hook("code_only_modules") == {"One AI": ["One"]}


def test_what_a_workspace_administers_is_in_one():
	assert {"AI Action Setting", "AI Credits", "AI Chat", "AI Proposal"} <= _links(ONE)


def test_what_the_operator_does_is_in_one_admin():
	assert {"AI Model", "AI Usage"} <= _links(ADMIN)


def test_a_workspaces_credits_are_its_administrators_and_its_own():
	report = json.loads((CREDITS / "ai_credits.json").read_text())
	assert [r["role"] for r in report["roles"]] == ["Workspace Administrator"]
	assert "roles.require()" in (CREDITS / "ai_credits.py").read_text()
	proxy = PROXY.read_text()
	said = proxy[proxy.index("def ai_usage("):]
	said = said[: said.index("\n@frappe.whitelist")]
	assert "caller()" in said, "a workspace could ask for another's usage"
	assert "tenant=" not in said.split("caller()")[0], "the tenant comes from the token, not the body"


def test_a_settings_page_is_a_record_with_help_on_every_field():
	"""A Single's route has no name, so it was read as a list; and every field
	on one gets a mark that asks what it is for."""
	js = (tree.APP / "public" / "js" / "oneai.js").read_text()
	assert "single ? route[1]" in js
	assert "frm.meta.issingle && !PROSE.includes(df.fieldtype)" in js and "onedesk.oneai.explain" in js
	suggest = (tree.APP / "one_ai" / "suggest.py").read_text()
	assert "issingle" in suggest and "Help me set this up" in suggest
	panel = (tree.APP / "public" / "js" / "oneai" / "Panel.vue").read_text()
	assert "opening && opening.ask" in panel
