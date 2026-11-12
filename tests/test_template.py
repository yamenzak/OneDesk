"""The release's template site is the last one migrated unless migrating
cannot give what installing would (deploy/release/template.py)."""

import ast
import importlib.util
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

HOOKS = '''after_sync = ["onedesk.one.brand.apply", "onedesk.one.roles.ensure"]
after_migrate = ["onedesk.one.roles.ensure"]
after_app_install = []
required_apps = ["erpnext", "hrms"]
doc_events = {"User": {"on_update": "onedesk.one.people.saved"}}
'''
BRAND = '''import frappe

from onedesk.one import paint

LOGO = "/one.svg"
DEFAULTS = {"Website Settings": {"app_logo": LOGO}}


def apply():
	"""Writes the defaults."""
	paint.colour()
	for doctype, values in DEFAULTS.items():
		frappe.db.set_single_value(doctype, values)


def mark(app):
	return app
'''
PAINT = '''def colour():
	return "blue"


def other():
	return 1
'''
BOOKS = '''from onedesk.one_admin import site


def ensure():
	if not site.is_admin() or not frappe.db.table_exists("Account"):
		return
	make_accounts()
'''


def _rule():
	spec = importlib.util.spec_from_file_location("template_rule", tree.ROOT / "deploy" / "release" / "template.py")
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


def _tree(changed: dict | None = None):
	held = {
		"onedesk/hooks.py": HOOKS,
		"onedesk/one/brand.py": BRAND,
		"onedesk/one/paint.py": PAINT,
		"onedesk/one_admin/books.py": BOOKS,
		"onedesk/modules.txt": "One\nOne HR\n",
	}
	held.update(changed or {})
	return {path: text for path, text in held.items() if text is not None}


def _why(old: dict, new: dict) -> list[str]:
	changes = [("D" if path not in new else "A" if path not in old else "M", path) for path in sorted(set(old) | set(new)) if old.get(path) != new.get(path)]
	return _rule().reasons(changes, old.get, new.get)


def _record(doctype, name, **values):
	return json.dumps({"doctype": doctype, "name": name, "modified": "2026-11-01 10:00:00", **values})


def test_where_a_file_sits_says_what_a_site_holds_of_it():
	kind = _rule().kind
	assert kind("onedesk/one_crm/report/lead_sources/lead_sources.json") == ("standard", "report")
	assert kind("onedesk/one/print_format/one_invoice/one_invoice.json") == ("standard", "print_format")
	assert kind("onedesk/one_hr/one_hr_dashboard/attendance/attendance.json") == ("standard", "dashboard")
	assert kind("onedesk/dock/onedesk/onedesk.json") == ("standard", "dock")
	assert kind("onedesk/fixtures/role.json") == ("fixture", "")
	assert kind("onedesk/one_hr/custom/employee.json") == ("custom", "")
	assert kind("onedesk/hooks.py") == ("hooks", "")
	assert kind("onedesk/one/data/countries.json") is None
	assert kind("onedesk/public/js/desk.js") is None



def test_an_ordinary_change_migrates():
	assert _why(_tree(), _tree()) == []
	assert _why(_tree(), _tree({"onedesk/one/paint.py": PAINT.replace("return 1", "return 2")})) == [], "a function no install hook reaches"
	assert _why(_tree(), _tree({"onedesk/one/brand.py": BRAND.replace("return app", "return None")})) == []
	assert _why(_tree(), _tree({"onedesk/one/brand.py": BRAND.replace("Writes the defaults.", "The defaults.")})) == [], "a docstring is no code"
	assert _why(_tree(), _tree({"onedesk/modules.txt": "One\nOne HR\nOne CRM\n"})) == []
	assert _why(_tree(), _tree({"onedesk/one_crm/report/x/x.json": _record("Report", "X")})) == []


def test_code_only_an_install_runs_installs_afresh():
	said = _why(_tree(), _tree({"onedesk/one/brand.py": BRAND.replace('"/one.svg"', '"/two.svg"')}))
	assert said == ["onedesk.one.brand.LOGO: changed, and it runs only at install"]
	said = _why(_tree(), _tree({"onedesk/one/paint.py": PAINT.replace('"blue"', '"red"')}))
	assert said == ["onedesk.one.paint.colour: changed, and it runs only at install"], "what it imports counts"


def test_an_install_hook_that_does_nothing_off_the_admin_site_is_no_reason():
	hooks = HOOKS.replace('"onedesk.one.roles.ensure"]\nafter_migrate', '"onedesk.one.roles.ensure", "onedesk.one_admin.books.ensure"]\nafter_migrate')
	old = _tree({"onedesk/hooks.py": hooks})
	assert _why(old, _tree({"onedesk/hooks.py": hooks, "onedesk/one_admin/books.py": BOOKS.replace("make_accounts()", "make_more()")})) == []
	assert _rule()._admin_only(ast.parse(BOOKS).body[1])
	assert not _rule()._admin_only(ast.parse(BRAND).body[4])


def test_hooks_read_only_at_install_install_afresh():
	assert _why(_tree(), _tree({"onedesk/hooks.py": HOOKS.replace('["erpnext", "hrms"]', '["erpnext"]')})) == ["onedesk/hooks.py: required_apps changed, and it is read only at install"]
	assert _why(_tree(), _tree({"onedesk/hooks.py": HOOKS.replace("people.saved", "people.kept")})) == [], "a doc event is read when it fires"
	added = HOOKS.replace('"onedesk.one.roles.ensure"]\nafter_migrate', '"onedesk.one.roles.ensure", "onedesk.one.paint.colour"]\nafter_migrate')
	assert any("onedesk.one.paint.colour runs only at install" in one for one in _why(_tree(), _tree({"onedesk/hooks.py": added})))
	both = added.replace('after_migrate = ["onedesk.one.roles.ensure"]', 'after_migrate = ["onedesk.one.roles.ensure", "onedesk.one.paint.colour"]')
	assert _why(_tree(), _tree({"onedesk/hooks.py": both})) == [], "a hook migrate runs too"
	gone = HOOKS.replace('"onedesk.one.roles.ensure"]\nafter_migrate = ["onedesk.one.roles.ensure"]', ']\nafter_migrate = []')
	assert any("onedesk.one.roles.ensure no longer runs" in one for one in _why(_tree(), _tree({"onedesk/hooks.py": gone})))


def test_what_migrate_never_takes_away_installs_afresh():
	assert _why(_tree(), _tree({"onedesk/modules.txt": "One\n"})) == ["onedesk/modules.txt: One HR left, and migrate keeps a Module Def"]
	page = {"onedesk/one/print_format/p/p.json": _record("Print Format", "P")}
	assert _why(_tree(page), _tree()) == ["Print Format P: its file is gone or holds it no longer, and migrate leaves it on the site"]
	moved = {"onedesk/one_factory/print_format/p/p.json": _record("Print Format", "P")}
	assert _why(_tree(page), _tree(moved)) == [], "a record moved to another module is still imported"
	report = {"onedesk/one/report/r/r.json": _record("Report", "R")}
	assert _why(_tree(report), _tree()) == [], "migrate reaps a standard report whose file is gone"
	fixture = json.dumps([{"doctype": "Role", "name": "A"}, {"doctype": "Role", "name": "B"}])
	assert _why(_tree({"onedesk/fixtures/role.json": fixture}), _tree({"onedesk/fixtures/role.json": json.dumps([{"doctype": "Role", "name": "A"}])})) == [
		"Role B: its file is gone or holds it no longer, and migrate leaves it on the site"
	]
	custom = json.dumps({"doctype": "Employee", "sync_on_migrate": 1, "custom_fields": [{"dt": "Employee", "fieldname": "one_a"}], "property_setters": []})
	bare = json.dumps({"doctype": "Employee", "sync_on_migrate": 1, "custom_fields": [], "property_setters": []})
	assert _why(_tree({"onedesk/one_hr/custom/employee.json": custom}), _tree({"onedesk/one_hr/custom/employee.json": bare})) == [
		"custom_fields Employee one_a: taken out of custom/, and migrate leaves it on the site"
	]
	assert _why(_tree({"onedesk/one_hr/custom/employee.json": custom}), _tree({"onedesk/one/custom/employee.json": custom})) == []
	unsynced = custom.replace('"sync_on_migrate": 1', '"sync_on_migrate": 0')
	assert _why(_tree(), _tree({"onedesk/one_hr/custom/employee.json": unsynced})) == ["onedesk/one_hr/custom/employee.json: has no sync_on_migrate, so only an install reads it"]


def test_a_value_frappe_keeps_from_the_site_installs_afresh():
	old = _tree({"onedesk/one/report/r/r.json": _record("Report", "R", disabled=0, ref_doctype="Lead")})
	assert _why(old, _tree({"onedesk/one/report/r/r.json": _record("Report", "R", disabled=1, ref_doctype="Lead")})) == [
		"Report R: its disabled changed, and frappe keeps the site's own when it imports it again"
	]
	assert _why(old, _tree({"onedesk/one/report/r/r.json": _record("Report", "R", disabled=0, ref_doctype="Task")})) == []



def test_other_upstream_commits_install_afresh():
	assert _why({"upstream.json": "{}"}, {"upstream.json": '{"frappe": {}}'}) == ["upstream.json changed: frappe, erpnext and hrms are other commits"]


def test_a_changed_record_is_imported_again_whatever_its_modified_says():
	changes = [
		("M", "onedesk/one/print_format/p/p.json"),
		("A", "onedesk/one/sidebar/s/s.json"),
		("M", "onedesk/one/doctype/thing/thing.json"),
		("D", "onedesk/one/page/gone/gone.json"),
		("M", "onedesk/one/brand.py"),
	]
	files = {
		"onedesk/one/print_format/p/p.json": _record("Print Format", "P"),
		"onedesk/one/sidebar/s/s.json": _record("Sidebar", "S"),
		"onedesk/one/doctype/thing/thing.json": _record("DocType", "Thing"),
	}
	assert _rule().stale(changes, files.get) == [["Print Format", "P"], ["Sidebar", "S"]]


def test_this_app_can_be_read_by_the_rule():
	rule = _rule()
	hooks = (tree.APP / "hooks.py").read_text(encoding="utf-8")
	paths = rule.at_install(hooks)
	assert paths, "after_sync, after_migrate and the install hooks stay plain lists"

	def read(path):
		found = tree.ROOT / path
		return found.read_text(encoding="utf-8") if found.is_file() else None

	reached = rule.fingerprint(paths, read)
	assert {one.rsplit(".", 1)[0] for one in paths} <= {one.rsplit(".", 1)[0] for one in reached}, "every install hook is found"


def test_the_build_migrates_the_kept_template_and_says_how_it_was_made():
	build = (tree.ROOT / "deploy" / "release" / "build.sh").read_text()
	flow = (tree.ROOT / ".github" / "workflows" / "release-assets.yml").read_text()
	assert build.count("spares.as_template") == 1, "a migrated template is emptied of a site's own as an installed one is"
	assert build.index("installed afresh") < build.index("spares.as_template")
	assert 'echo "$sha" > "$template/commit"' in build
	assert "fetch-depth: 0" in flow, "the rule reads the commit the kept template was made at"
	assert "restore-keys: ${{ steps.base.outputs.templates }}" in flow
	assert "hashFiles('deploy/release/template.py')" in flow, "a new rule starts afresh"
