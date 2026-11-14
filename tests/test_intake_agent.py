"""OneIntake as an employee: after the planners, OneAI reads what arrived
with tools in hand and acts through the one door.

What holds it: the model acts only through `act.apply` (marked, undoable,
checked against the person OneIntake reads for), it is shown what was
already done, it runs as that person and not as Administrator, a weak link
waits for a person like any unsure change, and a personal or historic
document is left to the planners."""

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

INTAKE = tree.APP / "one_ai" / "reading"
AGENT = INTAKE / "employee.py"


def _fn(where: Path, name: str) -> str:
	for node in ast.walk(ast.parse(where.read_text(encoding="utf-8"))):
		if isinstance(node, ast.FunctionDef) and node.name == name:
			return ast.unparse(node)
	raise AssertionError(f"{name} is not in {where.name}")


def test_every_hand_writes_through_the_one_door():
	source = AGENT.read_text(encoding="utf-8")
	for tool in ("link_to", "make_record", "fill_in", "add_comment", "make_task"):
		assert "_done(act.Action(" in _fn(AGENT, tool), tool
	done = _fn(AGENT, "_done")
	assert "act.apply(action, reading)" in done
	for raw in ("insert(", ".save(", "db.set_value", "db_set(", "ignore_permissions"):
		assert raw not in source, f"the agent writes around the door: {raw}"


def test_it_runs_as_the_person_and_hands_their_session_back():
	think = _fn(AGENT, "think")
	assert "frappe.set_user(reading.on_behalf_of)" in think
	assert think.index("finally:") < think.index("frappe.set_user(was)")
	assert "tools=(looks + HANDS, ())" in think and "taker(reading)" in think, "its own tools, as the agent that took it in"


def test_it_is_shown_what_was_done_and_told_not_to_repeat_it():
	assert "already_done" in _fn(AGENT, "told")
	sys.path.insert(0, str(tree.ROOT))
	from onedesk.one_ai import jobs

	said = jobs.words("intake_act")
	assert jobs.JOBS["intake_act"].tools and "already_done" in said
	assert "never touch invoices, payments or orders" in said


def test_a_personal_or_historic_document_is_left_to_the_planners():
	worth = _fn(AGENT, "_worth")
	assert "reading.history" in worth and "Ordinary" in worth and "copy_of" in worth


def test_a_weak_link_waits_like_any_unsure_change():
	level = _fn(INTAKE / "act.py", "level")
	assert "action.kind in CHANGES or action.kind == 'Link'" in level


def test_the_agent_comes_after_the_planners():
	act_now = _fn(INTAKE / "matters.py", "act_now")
	assert act_now.index("'the rest'") < act_now.index("employee.think(name)")
