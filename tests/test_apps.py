"""Apps a workspace turns off: hidden from the rail, search and pickers, never
refused. See one/apps.py."""

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

APPS = tree.APP / "one" / "apps.py"
HOOKS = (tree.APP / "hooks.py").read_text(encoding="utf-8")
JS = (tree.APP / "public" / "js" / "apps.js").read_text(encoding="utf-8")


def _load(names):
	space = {}
	for node in ast.parse(APPS.read_text()).body:
		if isinstance(node, ast.FunctionDef) and node.name in names:
			exec(ast.unparse(node), space)
	return space


def test_a_type_leaves_search_only_when_every_app_listing_it_is_off():
	unlisted = _load({"unlisted"})["unlisted"]
	lists = {"OneBook": {"Sales Invoice", "Customer"}, "OneCRM": {"Opportunity", "Customer"}, "OneTask": {"Task"}}
	assert unlisted(lists, {"OneCRM"}) == {"Opportunity"}, "Customer stays: OneBook lists it"
	assert unlisted(lists, {"OneCRM", "OneBook"}) == {"Opportunity", "Customer", "Sales Invoice"}
	assert unlisted(lists, set()) == set()


def test_turning_an_app_off_hides_and_never_refuses():
	"""Nothing in has_permission or frappe's disabled-app switch: OneIntake
	checks has_permission before it files, so a refusal would stop it."""
	source = APPS.read_text()
	assert "has_permission" not in source and "app_state" not in source
	assert '"onedesk.one.apps.boot"' in HOOKS
	assert '"frappe.desk.search.search_link": "onedesk.one.apps.search_link"' in HOOKS
	assert '"/assets/onedesk/js/apps.js"' in HOOKS
	assert "roles.require()" in source.split("def save(")[1].split("def ")[0], "a workspace administrator's"
	assert 'KEPT = ("One", "OneAdmin", "One Admin")' in source, "One's own Home and the operators' never go"
	companions = (tree.APP / "one" / "companions.py").read_text()
	assert "row.get(\"link_to\") not in off" in companions, "the site's Dock layer hides them"
	assert 'frappe.user.has_role("Workspace Administrator")' in JS and ".dock-user" in JS
	assert "build_options" in JS and 'frappe.ui.form.on("*"' in JS


def test_a_turned_off_apps_records_open_elsewhere():
	outside = (tree.APP / "one" / "outside.py").read_text()
	assert "name not in off" in outside and "apps.rehome(said)" in outside
	readme = (tree.APP / "one" / "README.md").read_text()
	assert "**Apps**, at the bottom of the rail" in readme.split("## Under the hood")[0], "how_to answers it"


def test_oneai_and_oneintake_off_leave_ones_sidebar_and_others_links():
	space = _load({"_where", "sectioned"})
	space.update(json=__import__("json"), AI="OneAI", MEMORY={"link_to": "settings", "route_options": {"section": "memory"}})
	items = [
		{"type": "Link", "label": "What OneAI Remembers", "link_to": "settings", "route_options": '{"section": "memory"}'},
		{"type": "Section Break", "label": "OneAI"},
		{"type": "Link", "label": "Actions", "link_to": "workspace-settings", "route_options": '{"section": "oneai"}'},
		{"type": "Section Break", "label": "OneIntake"},
		{"type": "Link", "label": "Ready to Submit", "link_to": "Ready to Submit"},
		{"type": "Section Break", "label": "Audit Log"},
		{"type": "Link", "label": "Changes", "link_to": "Version"},
	]
	kept, gone = space["sectioned"](items, {"OneIntake"})
	assert [one["label"] for one in kept] == ["What OneAI Remembers", "OneAI", "Actions", "Audit Log", "Changes"]
	assert gone == {("Ready to Submit", "null")}
	kept, gone = space["sectioned"](items, {"OneAI", "OneIntake"})
	assert [one["label"] for one in kept] == ["Audit Log", "Changes"], "What OneAI Remembers goes with OneAI"
	assert ("workspace-settings", '{"section": "oneai"}') in gone


def test_oneai_off_refuses_every_model_call_and_oneintake_needs_it():
	source = APPS.read_text()
	assert "NEEDS = {INTAKE: AI}" in source
	run = (tree.APP / "one_ai" / "run.py").read_text()
	assert run.count("apps.refuse_ai()") == 2, "run.ask and run.once, the only two that ask a model"
	assert run.count('"onedesk.one_admin.proxy.ai_run"') == 2
	pipeline = (tree.APP / "one_intake" / "pipeline.py").read_text()
	assert pipeline.count("apps.intake_on()") == 2, "pipeline.later and again"
	switches = (tree.APP / "one_intake" / "switches.py").read_text()
	assert switches.count("_reading()") == 4
	assert "data-needs" in JS and "is-locked" in JS


def test_reading_switches_live_in_one_not_in_onemail_or_onecloud():
	for path in (tree.ROOT / "frontend" / "src" / "mail" / "OneMail.vue", tree.ROOT / "frontend" / "src" / "cloud" / "OneCloud.vue"):
		source = path.read_text()
		assert "switches.set_mailbox" not in source and "switches.set_folder" not in source, path.name
