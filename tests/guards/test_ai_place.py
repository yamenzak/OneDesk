"""OneAI is a rail of its own (docs/ONE.md, stage 6): Documents, the
conversations, suggestions and knowledge, its reports and AICenter, which
were One's OneAI group. What the operator does lives in OneAdmin.

What is AI is drawn one way: onedesk.oneai.tag and onedesk.oneai.button
(public/js/one_ai/oneai.js, oneai.css). docs/STANDARD.md, point 16."""

import ast
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import tree

ONE = tree.APP / "one" / "sidebar" / "one" / "one.json"
RAIL = tree.APP / "one_ai" / "sidebar" / "oneai" / "oneai.json"
DOCK = tree.APP / "dock" / "onedesk" / "onedesk.json"
ADMIN = tree.APP / "one_admin" / "sidebar" / "one_admin" / "one_admin.json"
CREDITS = tree.APP / "one_ai" / "report" / "ai_credits"
PROXY = tree.APP / "one_admin" / "proxy.py"
JS = tree.APP / "public" / "js"
HELD = {"AI Credits", "AI Chat", "AI Proposal", "AI Knowledge", "intake"}


def _hook(name: str):
	for node in ast.parse(tree.hooks()).body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", None) == name:
			return ast.literal_eval(node.value)
	return None


def _read(path: Path) -> dict:
	return json.loads(path.read_text())


def links(sidebar: dict) -> set[str]:
	"""What a Sidebar's links open. Pure."""
	return {i.get("link_to") for i in sidebar["items"] if i.get("type") == "Link"}


def off_the_dock(code_only, dock: dict, rail: dict) -> list[str]:
	"""Why OneAI would not be a rail of its own on the dock. Pure."""
	out = ["One AI is a code-only module"] if "One AI" in code_only else []
	if "OneAI" not in {one["link_to"] for one in dock["items"]}:
		out.append("the dock has no OneAI")
	if rail["module"] != "One AI":
		out.append("OneAI's rail is not One AI's")
	return out


def misplaced(rail: dict, one: dict) -> list[str]:
	"""What a workspace administers of OneAI that is not in its rail, or is in
	One's. One's rail has AICenter only as one of its Centers (docs/READY.md,
	mechanism 18), never OneAI's own screens. Pure."""
	out = []
	if not (HELD <= links(rail) and not HELD & links(one)):
		out.append("OneAI's records are not in its rail alone")
	if "/desk/one?center=ai" not in {i.get("url") for i in rail["items"] if i.get("type") == "Link"}:
		out.append("AICenter is not on OneAI's rail")
	labels = [i.get("label") for i in one["items"]]
	if "OneAI" in labels or "AICenter" not in labels or "Centers" not in labels or labels.index("AICenter") < labels.index("Centers"):
		out.append("One's rail has OneAI other than AICenter among its Centers")
	return out


def operator_misplaced(admin: dict) -> bool:
	"""Whether OneAdmin's rail lacks AI Usage or offers AI Model. Pure."""
	return "AI Usage" not in links(admin) or "AI Model" in links(admin)


def credits_problems(report: dict, script: str, proxy: str) -> list[str]:
	"""Why a workspace's credits would not be its administrator's and its own. Pure."""
	out = []
	if [r["role"] for r in report["roles"]] != ["Workspace Administrator"]:
		out.append("the report is not the administrator's alone")
	if "roles.require()" not in script:
		out.append("the report does not require the role")
	said = proxy[proxy.index("def ai_usage(") :]
	said = said[: said.index("\n@frappe.whitelist")]
	if "caller()" not in said:
		out.append("a workspace could ask for another's usage")
	elif "tenant=" in said.split("caller()")[0]:
		out.append("the tenant comes from the token, not the body")
	return out


def marked_fields(js: str, edit: str, suggest: str, panel: str) -> list[str]:
	"""Where a settings page is read as a list, or a field, mail window or page
	field carries a OneAI button. Pure."""
	out = []
	if "single ? route[1]" not in js:
		out.append("a Single read as a list")
	fields = js[js.index("onedesk.oneai.fields = function") : js.index("onedesk.oneai.made = function")]
	if "<button" in fields or "one-ai-help" in js:
		out.append("a button beside a field's label")
	if "this.justLeft()" not in js or "JUST_LEFT_MS" not in js:
		out.append("the field just left is not what OneAI writes")
	if "one-ai-write" in js or "await this.inMail()" not in js:
		out.append("a OneAI button in the mail window")
	if '<button\n        v-if="writable && long' in edit or "aiLeft(" not in edit:
		out.append("a OneAI button beside a page's field")
	if "issingle" not in suggest or "Help me set this up" not in suggest:
		out.append("a settings page offers no setting up")
	if "opening && opening.ask" not in panel or "opening && opening.about" not in panel:
		out.append("the panel does not open on what it was asked")
	return out


def oneai_buttons(text: str) -> list[str]:
	"""The custom buttons a desk script adds for OneAI. Pure."""
	return [
		call.group(1)[:80]
		for call in re.finditer(r"add_custom_button\((.{0,400}?)\);", text, re.S)
		if re.search(r"__\(\"OneAI\"\)|onedesk\.one_ai|one_hr\.hiring\.|oneai\.", call.group(1))
	]


def drawn_unlike_frappe(oneai: str, css: str) -> list[str]:
	"""Where the tag and the button are not frappe's own in OneAI's colours. Pure."""
	out = []
	if "onedesk.oneai.tag = " not in oneai or "frappe.ui.badge.html(" not in oneai:
		out.append("the tag is not frappe's badge")
	if "onedesk.oneai.button = " not in oneai or "frappe.ui.button.html(" not in oneai:
		out.append("the button is not frappe's button")
	if '"[data-one-ai-ask]"' not in oneai:
		out.append("a button asks its question wherever it is drawn")
	out += [f"{part} is not styled" for part in (".es-badge.one-ai-tag", ".es-button.one-ai-button") if part not in css]
	if "var(--one-ai-spectrum) border-box" not in css:
		out.append("not in OneAI's colours")
	return out


def hand_badges(source: str) -> list[str]:
	"""frappe badges a desk script draws for OneAI itself. Pure."""
	return [badge for badge in re.findall(r"frappe\.ui\.badge\.html\(\{[^}]*\}", source) if "OneAI" in badge]


def hand_buttons(source: str) -> list[str]:
	"""Shell buttons a desk script draws for OneAI itself. Pure."""
	return [call for call in re.findall(r"onedesk\.shell\.button\([^;]*?\)", source) if "OneAI" in call or '"sparkles"' in call]


def test_one_ai_is_on_the_dock_with_a_rail_of_its_own():
	"""Its records open in its own rail, so it is no code-only module."""
	found = off_the_dock(_hook("code_only_modules"), _read(DOCK), _read(RAIL))
	assert not found, found


def test_what_a_workspace_administers_of_it_is_in_its_rail_not_ones():
	found = misplaced(_read(RAIL), _read(ONE))
	assert not found, found


def test_what_the_operator_does_is_in_one_admin():
	assert not operator_misplaced(_read(ADMIN))


def test_a_workspaces_credits_are_its_administrators_and_its_own():
	found = credits_problems(_read(CREDITS / "ai_credits.json"), (CREDITS / "ai_credits.py").read_text(), PROXY.read_text())
	assert not found, found


def test_a_settings_page_is_a_record_and_no_field_carries_a_mark():
	"""A Single's route has no name, so it was read as a list. No field, mail
	window or page field carries a OneAI button: the field the reader was in
	when they opened the panel is what it writes, or what the question is
	about, and an open mail window is what it writes in."""
	found = marked_fields(
		(JS / "one_ai" / "oneai.js").read_text(),
		(tree.ROOT / "frontend" / "src" / "kit" / "FieldEdit.vue").read_text(),
		(tree.APP / "one_ai" / "suggest.py").read_text(),
		(JS / "one_ai" / "panel" / "Panel.vue").read_text(),
	)
	assert not found, found


def test_no_oneai_button_on_a_page():
	"""Everything OneAI does is offered in its panel, for the page it opens on.

	A form carrying an AI button per feature is a form nobody reads, and a
	person looking for help looks in one place. A suggestion with `run` covers
	the things that are a job rather than a question; see one_ai/suggest.py.
	"""
	found = [
		f"{path.relative_to(tree.APP)}: {call!r}" for path in sorted(JS.rglob("*.js")) for call in oneai_buttons(path.read_text(encoding="utf-8"))
	]
	assert not found, "offer these in the OneAI panel instead:\n" + "\n".join(found)


def test_the_tag_and_the_button_are_frappes_own_in_oneais_colours():
	found = drawn_unlike_frappe(
		(JS / "one_ai" / "oneai.js").read_text(encoding="utf-8"),
		(tree.APP / "public" / "css" / "one_ai" / "oneai.css").read_text(encoding="utf-8"),
	)
	assert not found, found


def test_nothing_badges_oneai_by_hand():
	found = [f"{path.name}: {badge}" for path in sorted(JS.rglob("*.js")) for badge in hand_badges(path.read_text(encoding="utf-8"))]
	assert not found, "use onedesk.oneai.tag for " + ", ".join(found)


def test_no_oneai_button_is_drawn_by_hand():
	found = [f"{path.name}: {call}" for path in sorted(JS.rglob("*.js")) for call in hand_buttons(path.read_text(encoding="utf-8"))]
	assert not found, "use onedesk.oneai.button for " + ", ".join(found)


def test_the_place_rules_catch_their_examples():
	rail = {"module": "One AI", "items": [{"type": "Link", "link_to": one} for one in HELD] + [{"type": "Link", "url": "/desk/one?center=ai"}]}
	one = {"items": [{"label": "Centers"}, {"label": "AICenter"}]}
	assert not off_the_dock([], {"items": [{"link_to": "OneAI"}]}, rail)
	assert len(off_the_dock(["One AI"], {"items": []}, {"module": "One"})) == 3
	assert not misplaced(rail, one)
	assert len(misplaced({"items": []}, {"items": [{"label": "OneAI", "type": "Link", "link_to": "AI Chat"}]})) == 3
	assert operator_misplaced({"items": [{"type": "Link", "link_to": "AI Model"}]})
	assert not operator_misplaced({"items": [{"type": "Link", "link_to": "AI Usage"}]})
	proxy = "def ai_usage(tenant=None):\n\treturn usage(tenant)\n\n@frappe.whitelist()\ndef other(): pass\n"
	assert credits_problems({"roles": [{"role": "System Manager"}]}, "", proxy) == [
		"the report is not the administrator's alone",
		"the report does not require the role",
		"a workspace could ask for another's usage",
	]
	js = "onedesk.oneai.fields = function () { '<button>' }; onedesk.oneai.made = function () {}"
	assert len(marked_fields(js, "", "", "")) == 7
	assert oneai_buttons('frm.add_custom_button(__("OneAI"), () => go());')
	assert not oneai_buttons('frm.add_custom_button(__("Approve"), () => go());')
	assert len(drawn_unlike_frappe("", "")) == 6
	assert hand_badges('frappe.ui.badge.html({label: "OneAI"})') and not hand_badges('frappe.ui.badge.html({label: "Draft"})')
	assert hand_buttons('onedesk.shell.button({icon: "sparkles"})') and not hand_buttons('onedesk.shell.button({icon: "plus"})')
