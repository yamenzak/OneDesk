"""Point 2: a rule lives on the record, in its hooks, so it holds however the
record is changed: the page, the form, a bulk edit, a report view cell or a
Data Import row. These read the code."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "onedesk"
HOOKS = (APP / "hooks.py").read_text()
SUITE = (APP / "one_demo" / "check.py").read_text()

#: Each rule: the record, the hook that holds it, the fields it owns, and the
#: check that changes it every way on the demo.
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
	("User", "onedesk.one.settings.seated", {"enabled"}, "nobody_is_turned_on_past_the_seats"),
	("Employee", "onedesk.one_hr.everybody.employee", {"create_user_permission"}, "a_manager_is_not_kept_to_their_own_records"),
	("File", "onedesk.one_intake.switches.file_switched", {"one_intake", "one_intake_for"}, "a_folder_reads_for_whoever_turned_it_on"),
	("File", "onedesk.one_project.media.kept_shown", {"one_featured", "is_private"}, None),
	("Task", "onedesk.one_task.task.before_validate", {"progress"}, "a_tasks_progress_is_its_checklist"),
	("Email Account", "onedesk.one_intake.switches.mailbox_switched", {"one_intake", "one_intake_for"}, None),
	("Email Account", "onedesk.one_mail.holders.signed", {"add_signature"}, None),
	("Purchase Order", "onedesk.one_inventory.order.within_requests", set(), "oneinventory_buying_from_request_to_order"),
	("Work Order", "onedesk.one_inventory.making.steps", {"operations"}, "oneinventory_making_from_bill_to_finished_goods"),
)

#: Direct writes to a field a rule owns, each with why it is not a way round.
ALLOWED = {
	("one/privacy.py", "_turn_off"): "turning somebody off takes no seat",
	("one/portal_invite.py", "invite_contact"): "a portal login is a Website User and takes no seat",
	("one/portal_invite.py", "revoke"): "a portal login is a Website User and takes no seat",
	("one/portal_invite.py", "restore"): "a portal login is a Website User and takes no seat",
	("one_intake/switches.py", "set_folder"): "asks what file_switched asks, without a File save",
	("one_project/budget.py", "sync"): "is the rule itself, run by the Budget's submit and cancel",
	("one_mail/holders.py", "set_signature"): "sets both fields as signed() does; a save would try the mail server",
}


def _hooked(doctype: str, path: str) -> bool:
	start = HOOKS.find(f'\t"{doctype}": {{')
	if start < 0:
		return False
	end = HOOKS.find("\n\t},", start)
	return f'"{path}"' in HOOKS[start:end]


def test_every_rule_is_on_its_records_hooks():
	missing = [(doctype, path) for doctype, path, _f, _c in RULES if not _hooked(doctype, path)]
	assert not missing, missing


def test_every_rule_is_changed_every_way_on_the_demo():
	assert 'WAYS = ("bulk edit", "report view", "import")' in SUITE
	missing = [check for *_r, check in RULES if check and f"def {check}(" not in SUITE]
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
	for path in APP.rglob("*.py"):
		rel = path.relative_to(APP).as_posix()
		if rel.startswith("one_demo/") or "/patches/" in f"/{rel}":
			continue
		for fn in ast.walk(ast.parse(path.read_text())):
			if not isinstance(fn, ast.FunctionDef):
				continue
			for call in ast.walk(fn):
				if not (isinstance(call, ast.Call) and ast.unparse(call.func) == "frappe.db.set_value" and call.args):
					continue
				doctype = getattr(call.args[0], "value", None)
				if _fields(call) & owned.get(doctype, set()) and (rel, fn.name) not in ALLOWED:
					found.append(f"{rel}:{call.lineno} {fn.name}")
	assert not found, found
