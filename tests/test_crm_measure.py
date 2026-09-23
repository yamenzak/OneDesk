"""What OneCRM is measured by, and the fact it rests on."""

import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

CRM = tree.APP / "one_crm"


def _pure(path, name):
	space = {}
	for node in ast.parse(path.read_text(encoding="utf-8")).body:
		if isinstance(node, ast.FunctionDef) and node.name == name:
			exec(ast.unparse(node), space)
	return space[name]


def test_the_win_rate_is_won_over_won_and_lost():
	rate = _pure(CRM / "measure.py", "rate")
	assert rate(1, 1) == 50.0
	assert rate(2, 1) == 66.7
	assert rate(0, 0) == 0.0, "no deals closed is not a division by zero"


def test_no_report_or_card_measures_by_modified():
	"""A deal corrected in May was not won in May."""
	for path in [CRM / "measure.py", *CRM.glob("report/*/*.py")]:
		assert '"modified"' not in path.read_text(encoding="utf-8"), path.name


def test_every_card_on_home_is_ours_and_worked_out_here():
	workspace = json.loads((CRM / "workspace" / "onecrm" / "onecrm.json").read_text())
	source = (CRM / "measure.py").read_text(encoding="utf-8")
	for row in workspace["number_cards"]:
		folder = row["number_card_name"].lower().replace(" ", "_").replace("(", "").replace(")", "")
		card = json.loads((CRM / "number_card" / folder / f"{folder}.json").read_text())
		assert card["type"] == "Custom" and card["module"] == "One CRM"
		assert f"def {card['method'].rsplit('.', 1)[1]}(" in source


def test_a_deal_and_its_quotation_share_one_list_of_reasons():
	deal = json.loads((tree.APP / "fixtures" / "opportunity_lost_reason.json").read_text())
	quote = json.loads((tree.APP / "fixtures" / "quotation_lost_reason.json").read_text())
	assert {row["name"] for row in deal} == {row["name"] for row in quote}


def test_no_report_asks_for_a_company():
	for path in CRM.glob("report/*/*.js"):
		assert 'fieldname: "company"' not in path.read_text(encoding="utf-8"), path.name


# ------------------------------------------------------------ time in stage


def _time_in_stage():
	from datetime import datetime
	from statistics import median

	def get_datetime(value):
		return value if isinstance(value, datetime) else datetime.fromisoformat(value)

	space = {"get_datetime": get_datetime, "median": median, "FEWEST": 3}
	for node in ast.parse((CRM / "measure.py").read_text(encoding="utf-8")).body:
		if isinstance(node, ast.FunctionDef) and node.name in ("stays", "days", "usual", "stuck"):
			exec(ast.unparse(node), space)
	return space


def test_a_stay_ends_when_the_next_move_is_written():
	stays = _time_in_stage()["stays"]
	moves = [
		{"reference_name": "A", "value": "New", "creation": "2026-09-01 09:00"},
		{"reference_name": "A", "value": "Qualified", "creation": "2026-09-03 09:00"},
		{"reference_name": "A", "value": "Qualified", "creation": "2026-09-04 09:00"},
		{"reference_name": "A", "value": "Proposal", "creation": "2026-09-08 09:00"},
		{"reference_name": "B", "value": "New", "creation": "2026-09-05 09:00"},
	]
	said = stays(moves)
	assert [(one["deal"], one["stage"], one["left"]) for one in said] == [
		("A", "New", "2026-09-03 09:00"),
		("A", "Qualified", "2026-09-08 09:00"),
		("A", "Proposal", None),
		("B", "New", None),
	], "a move to the stage a deal is already in is not a new stay, and B's first move does not end A's"


def test_what_is_usual_is_the_middle_and_needs_three():
	space = _time_in_stage()
	assert space["usual"]([2, 3]) is None
	assert space["usual"]([2, 3, 400]) == 3, "one forgotten deal does not move the usual"


def test_a_deal_is_stuck_only_past_the_usual_and_past_a_day():
	stuck = _time_in_stage()["stuck"]
	assert stuck(8, 5) and not stuck(4, 5)
	assert not stuck(0.5, 0.0), "a stage deals leave within the hour does not make every deal in it stuck"
	assert not stuck(30, None), "nothing is usual yet"
