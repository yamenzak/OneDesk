"""An empty date is not the earliest day.

frappe reads an empty date in a `<` or `<=` filter as 0001-01-01
(`IFNULL(field, '0001-01-01') < x`), so "snoozed until before now" also
finds every conversation nobody snoozed, and "shown until before now" every
announcement with no end. That woke every mailbox each night and every
inbox every few minutes, ended every announcement with no end, and put
undated tasks and work orders among the late ones.

A `<` or `<=` on a date in our code either says `["field", "is", "set"]`
beside it, or is listed in REVIEWED with why an empty one cannot reach it.
The list only shrinks: a new one is read and fixed, or read and added.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import tree

DATED = re.compile(r"(date|_on|_at|until|_till|expiry|_time|^time$)")
UNDATED = {"creation", "modified"}
AS_DICT = re.compile(r'"(\w+)"\s*:\s*[\[\(]\s*"(<=?)"')
AS_LIST = re.compile(r'\[\s*"(\w+)"\s*,\s*"(<=?)"')

ALWAYS = "always filled where it is read"
REVIEWED = {
	"one_admin/home.py::asked_on": "a domain's asked_on is written when it is added (domains.py)",
	"one_admin/home.py::next_run_at": "a provisioning job sets next_run_at on save",
	"one_admin/runner.py::next_run_at": "a provisioning job sets next_run_at on save",
	"one_book/checks.py::year_start_date": ALWAYS + ": a fiscal year's",
	"one_book/closing.py::year_end_date": ALWAYS + ": a fiscal year's",
	"one_book/home.py::due_date": ALWAYS + ": a submitted invoice's",
	"one_crm/tell.py::one_next_on": "bounded below by a > on the same field",
	"one_demo/career.py::holiday_date": ALWAYS + ": a holiday's",
	"one_demo/check.py::from_date": ALWAYS + ": a leave application's",
	"one_demo/check.py::start_date": ALWAYS + ": a shift assignment's",
	"one_demo/hr.py::from_date": ALWAYS + ": a leave application's",
	"one_demo/living.py::date_of_joining": ALWAYS + ": an employee's",
	"one_demo/living.py::from_date": ALWAYS + ": a leave application's and a salary structure assignment's",
	"one_factory/home.py::planned_start_date": ALWAYS + ": a work order's",
	"one_hr/accounts.py::year_start_date": ALWAYS + ": a fiscal year's",
	"one_hr/agent.py::from_date": ALWAYS + ": a leave application's and an attendance request's",
	"one_hr/ai_payroll.py::start_date": ALWAYS + ": a salary slip's",
	"one_hr/away.py::from_date": ALWAYS + ": a leave application's",
	"one_hr/calendar.py::from_date": ALWAYS + ": a leave application's",
	"one_hr/checks.py::from_date": ALWAYS + ": a leave application's",
	"one_hr/employee.py::from_date": ALWAYS + ": a salary structure assignment's",
	"one_hr/encashment.py::from_date": ALWAYS + ": a salary structure assignment's",
	"one_hr/gates.py::start_date": ALWAYS + ": a shift assignment's",
	"one_hr/home.py::from_date": ALWAYS + ": a leave application's",
	"one_hr/marking.py::time": ALWAYS + ": a check-in's",
	"one_hr/periods.py::from_date": ALWAYS + ": a leave period's",
	"one_hr/periods.py::start_date": ALWAYS + ": a payroll period's",
	"one_hr/presence.py::from_date": ALWAYS + ": a leave application's",
	"one_hr/story.py::from_date": ALWAYS + ": a salary structure assignment's",
	"one_hr/tell.py::scheduled_on": ALWAYS + ": an interview's",
	"one_inventory/checks.py::schedule_date": ALWAYS + ": a material request's",
	"one_inventory/view.py::posting_date": ALWAYS + ": a stock ledger entry's",
	"one_mail/faces.py::checked_on": "a face never checked is meant to be checked now",
	"one_mail/rules.py::communication_date": ALWAYS + ": a communication's",
	"one_mail/rules.py::from_date": ALWAYS + ": a leave application's",
	"one_project/checks.py::from_date": ALWAYS + ": a leave application's",
	"one_project/hours.py::from_time": ALWAYS + ": a timesheet row's",
	"one_project/report/workload/workload.py::from_date": ALWAYS + ": a leave application's",
	"one_project/site_time.py::start_date": ALWAYS + ": a shift assignment's",
	"one_project/view.py::exp_end_date": "bounded below by a >= on the same field",
	"one_cloud/api.py::one_deleted_on": "a file deleted before one_deleted_on was kept is old enough to empty",
	"one_task/tell.py::exp_end_date": "or_filters; a task with neither date is dropped by when(due(...))",
	"one_task/tell.py::exp_start_date": "or_filters; a task with neither date is dropped by when(due(...))",
}


def found(root: Path) -> set[str]:
	"""Each file and date field with a `<` or `<=` and no `is set` near it."""
	out = set()
	for path in root.rglob("*.py"):
		if {"tests", "patches"} & set(path.relative_to(root).parts):
			continue
		text = path.read_text(encoding="utf-8")
		for match in [*AS_DICT.finditer(text), *AS_LIST.finditer(text)]:
			field = match.group(1)
			if field in UNDATED or not DATED.search(field):
				continue
			near = text[max(0, match.start() - 400) : match.end() + 200]
			if re.search(rf'"{field}"\s*,\s*"is"\s*,\s*"set"', near):
				continue
			out.add(f"{path.relative_to(root).as_posix()}::{field}")
	return out


def test_every_date_before_something_says_it_is_set():
	new = sorted(found(tree.APP) - set(REVIEWED))
	assert not new, (
		"a < or <= on a date that may be empty finds every record without one; "
		'add ["field", "is", "set"], or read it and add it to REVIEWED with why:\n  ' + "\n  ".join(new)
	)


def test_reviewed_only_shrinks():
	gone = sorted(set(REVIEWED) - found(tree.APP))
	assert not gone, "these no longer need a reason; take them out of REVIEWED:\n  " + "\n  ".join(gone)


def test_the_guard_catches_a_snooze_with_no_is_set(tmp_path):
	(tmp_path / "team.py").write_text('frappe.get_all("Mail Conversation", filters={"snoozed_until": ["<=", now]})\n', encoding="utf-8")
	(tmp_path / "fixed.py").write_text('filters=[["snoozed_until", "is", "set"], ["snoozed_until", "<=", now]]\n', encoding="utf-8")
	assert found(tmp_path) == {"team.py::snoozed_until"}
