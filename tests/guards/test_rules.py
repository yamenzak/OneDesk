"""Point 2: a rule lives on the record, in its hooks, so it holds however the
record is changed: the page, the form, a bulk edit, a report view cell or a
Data Import row. These read the code."""

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "onedesk"
sys.path.insert(0, str(ROOT / "scripts"))

import tree  # noqa: E402

HOOKS = tree.hooks()
SUITE = tree.suite()

RULES = (
	("Project", "onedesk.one_project.status.held", {"status"}, "a_project_with_open_work_is_not_closed_by_hand"),
	(
		"Project",
		"onedesk.one_project.kinds.held",
		{"one_kind", "customer", "one_monthly_fee", "one_monthly_hours", "one_markup"},
		"an_internal_project_bills_nobody",
	),
	("Project", "onedesk.one_project.budget.summed", {"estimated_costing"}, "a_projects_budget_is_its_cost_types"),
	("Budget", "onedesk.one_project.budget.synced", set(), "a_cancelled_budget_leaves_its_project"),
	("Company", "onedesk.one_book.closing.kept_to_today", {"accounts_frozen_till_date"}, "the_books_lock_up_to_today_at_most"),
	("User", "onedesk.one.people.seated", {"enabled"}, "nobody_is_turned_on_past_the_seats"),
	("Employee", "onedesk.one_hr.everybody.employee", {"create_user_permission"}, "a_manager_is_not_kept_to_their_own_records"),
	("File", "onedesk.one_ai.reading.switches.file_switched", {"one_intake", "one_intake_for"}, "a_folder_reads_for_whoever_turned_it_on"),
	("File", "onedesk.one_project.media.kept_shown", {"one_featured", "is_private"}, None),
	("Task", "onedesk.one_task.task.before_validate", {"progress"}, "a_tasks_progress_is_its_checklist"),
	("Email Account", "onedesk.one_ai.reading.switches.mailbox_switched", {"one_intake", "one_intake_for"}, None),
	("Email Account", "onedesk.one_mail.holders.signed", {"add_signature"}, None),
	("Purchase Order", "onedesk.one_inventory.order.within_requests", set(), "oneinventory_buying_from_request_to_order"),
	("Work Order", "onedesk.one_factory.making.steps", {"operations"}, "onefactory_making_from_bill_to_finished_goods"),
	("Asset Maintenance", "onedesk.one_inventory.maintenance.due", set(), "oneinventory_equipment_bought_given_serviced_and_mended"),
	(
		"Asset Maintenance Log",
		"onedesk.one_inventory.maintenance.on_time",
		{"maintenance_status"},
		"oneinventory_equipment_bought_given_serviced_and_mended",
	),
)

ALLOWED = {
	("one/privacy.py", "_turn_off"): "turning somebody off takes no seat",
	("one_portal/invite.py", "invite_contact"): "a portal login is a Website User and takes no seat",
	("one_portal/invite.py", "revoke"): "a portal login is a Website User and takes no seat",
	("one_portal/invite.py", "restore"): "a portal login is a Website User and takes no seat",
	("one_ai/reading/switches.py", "set_folder"): "asks what file_switched asks, without a File save",
	("one_project/budget.py", "sync"): "is the rule itself, run by the Budget's submit and cancel",
	("one_mail/holders.py", "set_signature"): "sets both fields as signed() does; a save would try the mail server",
}


def _hooked(doctype: str, path: str, hooks: str = HOOKS) -> bool:
	start = hooks.find(f'\t"{doctype}": {{')
	if start < 0:
		return False
	end = hooks.find("\n\t},", start)
	return f'"{path}"' in hooks[start:end]


def test_every_rule_is_on_its_records_hooks():
	missing = [(doctype, path) for doctype, path, _f, _c in RULES if not _hooked(doctype, path)]
	assert not missing, missing


def unchanged(rules, suite: str) -> list[str]:
	"""The checks the rules name that the suite does not have, and WAYS if the
	suite does not change a record every way. Pure."""
	out = [] if 'WAYS = ("bulk edit", "report view", "import")' in suite else ["WAYS"]
	return out + [check for *_r, check in rules if check and f"def {check}(" not in suite]


def test_every_rule_is_changed_every_way_on_the_demo():
	missing = unchanged(RULES, SUITE)
	assert not missing, missing


def _fields(call: ast.Call) -> set:
	if len(call.args) < 3:
		return set()
	value = call.args[2]
	if isinstance(value, ast.Constant):
		return {value.value}
	if isinstance(value, ast.Dict):
		return {key.value for key in value.keys if isinstance(key, ast.Constant)}
	return set()


def test_no_endpoint_writes_round_a_rule():
	"""frappe.db.set_value skips the record's hooks. On a field a rule owns
	it decides the rule somewhere else."""
	owned = {}
	for doctype, _p, fields, _c in RULES:
		owned.setdefault(doctype, set()).update(fields)
	found = []
	for path in tree.scoped(APP.rglob("*.py")):
		rel = path.relative_to(APP).as_posix()
		if rel.startswith("one_demo/") or path.name in ("checks.py", "demo.py") or "/patches/" in f"/{rel}":
			continue
		if "set_value" not in tree.text(path):
			continue
		found += round_a_rule(tree.walked(path), rel, owned, ALLOWED)
	assert not found, found


def round_a_rule(nodes, rel: str, owned: dict, allowed: dict) -> list[str]:
	"""Each frappe.db.set_value among a file's nodes on a field a rule owns,
	in a function not allowed it. Pure."""
	found = []
	for fn in nodes:
		if not isinstance(fn, ast.FunctionDef):
			continue
		for call in ast.walk(fn):
			if not (isinstance(call, ast.Call) and ast.unparse(call.func) == "frappe.db.set_value" and call.args):
				continue
			doctype = getattr(call.args[0], "value", None)
			if _fields(call) & owned.get(doctype, set()) and (rel, fn.name) not in allowed:
				found.append(f"{rel}:{call.lineno} {fn.name}")
	return found


def test_the_rules_rules_catch_their_examples():
	hooks = 'doc_events = {\n\t"Task": {\n\t\t"validate": "onedesk.a.held",\n\t},\n\t"Note": {\n\t},\n}'
	assert _hooked("Task", "onedesk.a.held", hooks) and not _hooked("Note", "onedesk.a.held", hooks)
	rules = (("Task", "onedesk.a.held", {"status"}, "a_task_holds"),)
	assert unchanged(rules, "def a_task_holds(") == ["WAYS"]
	assert unchanged(rules, 'WAYS = ("bulk edit", "report view", "import")\n') == ["a_task_holds"]
	source = 'def close(name):\n\tfrappe.db.set_value("Task", name, "status", "Closed")\n'
	nodes = tuple(ast.walk(ast.parse(source)))
	assert round_a_rule(nodes, "one_task/x.py", {"Task": {"status"}}, {}) == ["one_task/x.py:2 close"]
	assert round_a_rule(nodes, "one_task/x.py", {"Task": {"status"}}, {("one_task/x.py", "close"): "why"}) == []
