"""OneAI in OneCRM: what it reads, the cards it writes, and when a deal is quiet.

The rules are OneAI's and this checks OneCRM keeps them: the reads check the
record as the person asking, every write is a card, a person already a lead is
not suggested twice, and a call the model writes up is the same Call Log the
dialog makes — which a salesperson may now approve.
"""

import ast
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

AI = tree.APP / "one_crm" / "ai.py"
HOOKS = tree.APP / "hooks.py"
ACCESS = tree.APP / "one_crm" / "access.py"


def _source(name: str) -> str:
	for node in ast.walk(ast.parse(AI.read_text(encoding="utf-8"))):
		if isinstance(node, ast.FunctionDef) and node.name == name:
			return ast.unparse(node)
	raise AssertionError(f"{name} is not in ai.py")


def _quiet():
	def get_datetime(value):
		return value if isinstance(value, datetime) else datetime.fromisoformat(value)

	space = {"get_datetime": get_datetime, "add_days": lambda when, days: when + timedelta(days=days)}
	exec(_source("quiet"), space)
	return space["quiet"]


NOW = datetime(2026, 9, 23, 12, 0)


@pytest.mark.parametrize(
	"spoke, next_on, days, gone",
	[
		("2026-09-01 10:00", None, 14, True),  # three weeks, nothing planned
		("2026-09-20 10:00", None, 14, False),  # spoke three days ago
		("2026-09-01 10:00", "2026-09-25 09:00", 14, False),  # something is planned
		("2026-09-01 10:00", "2026-09-10 09:00", 14, True),  # the plan's day passed
		("2026-09-14 10:00", None, 7, True),  # a lead waits a week, not two
	],
)
def test_a_deal_is_quiet_when_nobody_spoke_and_nothing_is_planned(spoke, next_on, days, gone):
	assert _quiet()(spoke, next_on, NOW, days) is gone


def test_every_tool_is_registered_as_a_read_or_a_card():
	hooks = HOOKS.read_text()
	reads = hooks.split("one_ai_reads = [", 1)[1].split("]", 1)[0]
	suggests = hooks.split("one_ai_suggests = [", 1)[1].split("]", 1)[0]
	for name in ("deal_facts", "lead_facts", "gone_quiet", "why_we_lose"):
		assert f"onedesk.one_crm.ai.{name}" in reads
	for name in ("add_lead", "plan_next_step", "write_up_call"):
		assert f"onedesk.one_crm.ai.{name}" in suggests
		assert "proposals.propose(" in _source(name)
	assert '"onedesk.one_crm.ai.SUGGESTIONS"' in hooks
	assert '"onedesk.one_crm.ai.workspace"' in hooks


def test_nothing_here_writes_except_through_a_card():
	said = AI.read_text()
	for verb in (".insert(", ".save(", "db.set_value", "db_set", "ignore_permissions"):
		assert verb not in said, verb


def test_a_record_is_read_as_the_person_asking():
	assert 'doc.check_permission("read")' in AI.read_text().split("def _facts(", 1)[1].split("\ndef ", 1)[0]
	assert "frappe.get_list(" in _source("gone_quiet")
	assert "measure.deals(" in _source("why_we_lose")


def test_a_person_already_a_lead_is_said_not_suggested():
	said = _source("add_lead")
	assert "capture.matches(" in said
	assert "one_duplicate_of" in said


def test_a_call_written_up_is_the_call_the_dialog_makes():
	assert "record.call(" in _source("write_up_call")
	record = (tree.APP / "one_crm" / "record.py").read_text()
	assert "frappe.get_doc(call(doc, direction, outcome, minutes, summary))" in record


def test_a_salesperson_may_approve_a_call():
	access = ACCESS.read_text()
	assert '"Call Log"' in access and "add_permission(" in access


def test_a_next_step_is_never_in_the_past():
	assert "has passed" in _source("plan_next_step")


def test_the_file_a_record_came_from_is_found_in_one_place():
	"""A CV and a business card are matched to their file by one function."""
	assert "files.uploaded(" in _source("add_lead")
	assert "files.uploaded(" in (tree.APP / "one_hr" / "ai.py").read_text()
	assert "def _cv(" not in (tree.APP / "one_hr" / "ai.py").read_text()
