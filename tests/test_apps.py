"""Apps a workspace turns off: hidden from the rail, search and pickers, never
refused. See one/apps.py."""

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

APPS = tree.APP / "one" / "apps.py"
HOOKS = tree.hooks()
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
	assert "app.kept.always()" in source, "One's own Home and the operators' never go"
	companions = (tree.APP / "one" / "companions.py").read_text()
	assert "row.get(\"link_to\") not in off" in companions, "the site's Dock layer hides them"
	assert "onedesk.rail.launcher()" in JS and ".dock-user" in JS, "the Apps button is everybody's launcher"
	launcher = (tree.APP / "public" / "js" / "one_interface" / "launcher.js").read_text()
	assert "if (frappe.boot.one_administers) {" in launcher and 'frappe.set_route("marketplace")' in launcher, "turning apps on or off stays an administrator's, in OneMarketplace"
	assert "onedesk.apps.configure" not in JS, "OneMarketplace is the one way in"
	assert "build_options" in JS and 'frappe.ui.form.on("*"' in JS


def test_a_turned_off_apps_records_open_elsewhere():
	outside = (tree.APP / "one" / "outside.py").read_text()
	assert "name not in off" in outside and "apps.rehome(said)" in outside
	help_page = (tree.APP / "one" / "help" / "settings.md").read_text()
	assert "**Apps**, at the bottom of the rail" in help_page, "how_to answers it"


def test_oneai_is_a_rail_and_reading_off_leaves_every_rail():
	"""OneAI is its own rail, turned off as any app is; what reading shows
	leaves every rail when reading is off, and What OneAI Remembers when
	OneAI is."""
	space = _load({"_where", "gone"})
	space.update(
		json=__import__("json"),
		AI="OneAI",
		INTAKE="Reading",
		MEMORY={"url": "/desk/one?center=ai&at=yours"},
		AI_CENTER={"url": "/desk/one?center=ai"},
		READS=({"link_to": "Ready to Submit"}, {"url": "/desk/one?center=ai&at=reads"}),
	)
	rows = [
		{"label": "What OneAI Remembers", "url": "/desk/one?center=ai&at=yours"},
		{"label": "What OneAI Reads", "url": "/desk/one?center=ai&at=reads"},
		{"label": "Ready to Submit", "link_to": "Ready to Submit"},
		{"label": "AICenter", "url": "/desk/one?center=ai"},
		{"label": "Changes", "link_to": "Version"},
	]
	kept = lambda off: [one["label"] for one in rows if space["_where"](one) not in space["gone"](off)]
	assert kept({"Reading"}) == ["What OneAI Remembers", "AICenter", "Changes"]
	assert kept({"OneAI", "Reading"}) == ["Changes"]
	assert kept(set()) == [one["label"] for one in rows]
	source = APPS.read_text()
	assert "SECTIONS = (INTAKE,)" in source
	rail = __import__("json").loads((tree.APP / "one_ai" / "sidebar" / "oneai" / "oneai.json").read_text())
	assert rail["name"] == "OneAI" and rail["module"] == "One AI"
	dock = __import__("json").loads((tree.APP / "dock" / "onedesk" / "onedesk.json").read_text())
	assert "OneAI" in [one["link_to"] for one in dock["items"]]


def test_oneai_off_refuses_every_model_call_and_oneintake_needs_it():
	source = APPS.read_text()
	assert "NEEDS = {INTAKE: AI}" in source
	run = (tree.APP / "one_ai" / "run.py").read_text()
	assert run.count("apps.refuse_ai()") == 5, "run.turn, run.once, run.read, run.make and run.begin, the only five that ask a model"
	assert run.count('"onedesk.one_admin.proxy.ai_run"') == 2
	pipeline = (tree.APP / "one_ai" / "reading" / "pipeline.py").read_text()
	assert pipeline.count("apps.intake_on()") == 2, "pipeline.later and again"
	switches = (tree.APP / "one_ai" / "reading" / "switches.py").read_text()
	assert switches.count("_reading()") == 4
	market = (tree.APP / "one" / "marketplace.py").read_text()
	assert "apps.NEEDS.get(row) != one.sidebar" in market, "what was off only because OneAI was comes back with it"


def test_reading_switches_live_in_one_not_in_onemail_or_onecloud():
	for path in (tree.ROOT / "frontend" / "src" / "mail" / "OneMail.vue", tree.ROOT / "frontend" / "src" / "cloud" / "OneCloud.vue"):
		source = path.read_text()
		assert "switches.set_mailbox" not in source and "switches.set_folder" not in source, path.name


def test_the_demo_company_is_for_dev_sites_only():
	"""Production never offers, builds or checks the demo company."""
	dev = (tree.APP / "one" / "dev.py").read_text()
	assert 'frappe.conf.get("one_dev")' in dev
	for path, name in (("one_demo/build.py", "def load("), ("one_demo/start.py", "def _may("), ("one_demo/check.py", "def run(")):
		body = (tree.APP / path).read_text().split(name, 1)[1].split("\ndef ", 1)[0]
		assert "dev.require()" in body, path
	assert "frappe.boot.one_dev &&" in (tree.APP / "public" / "js" / "setup_wizard.js").read_text()
	assert 'bootinfo["one_dev"] = dev.site()' in (tree.APP / "one" / "boot.py").read_text()


def test_an_app_with_an_agent_uses_oneais_credits():
	from types import SimpleNamespace

	from onedesk.one import marketplace

	assert marketplace.uses(SimpleNamespace(credits=(), agent="accountant")) == ("ai",)
	assert marketplace.uses(SimpleNamespace(credits=("ai",), agent="x")) == ("ai",)
	assert marketplace.uses(SimpleNamespace(credits=("mail",), agent=None)) == ("mail",)
