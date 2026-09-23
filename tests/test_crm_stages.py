"""A sales stage has a position, a probability and an outcome, and an
opportunity's status and probability follow it."""

import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

STAGES = tree.APP / "one_crm" / "stages.py"
HOOKS = (tree.APP / "hooks.py").read_text(encoding="utf-8")


def _module():
	space = {}
	for node in ast.parse(STAGES.read_text(encoding="utf-8")).body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") in ("SEVEN", "STATUS", "CLOSED", "HOLD"):
			exec(ast.unparse(node), space)
		if isinstance(node, ast.FunctionDef) and node.name == "probability":
			exec(ast.unparse(node), space)
	return space


def test_won_and_lost_are_certain_whatever_was_typed():
	probability = _module()["probability"]
	assert probability({"one_outcome": "Won"}, 40, was=40, moved=True) == 100
	assert probability({"one_outcome": "Lost"}, 90, was=90, moved=True) == 0


def test_a_stage_sets_the_probability_on_arrival_unless_one_was_typed():
	probability = _module()["probability"]
	proposal = {"one_outcome": "Open", "one_probability": 50}
	assert probability(proposal, 10, was=10, moved=True) == 50
	assert probability(proposal, None, moved=True) == 50
	assert probability(proposal, 65, was=10, moved=True) == 65, "typed in the same save"
	assert probability(proposal, 65, was=10, moved=False) == 65, "typed without moving"


def test_the_seven_are_in_order_with_one_won_one_lost_and_one_on_hold():
	seven = _module()["SEVEN"]
	positions = [position for _name, position, _chance, _outcome in seven]
	assert positions == sorted(positions) and len(set(positions)) == len(positions)
	outcomes = [outcome for *_rest, outcome in seven]
	assert outcomes.count("Won") == 1 and outcomes.count("Lost") == 1 and outcomes.count("On Hold") == 1
	assert outcomes.index("On Hold") < outcomes.index("Won"), "on hold sits before the closing stages"
	chances = [chance for _name, _position, chance, outcome in seven if outcome == "Open"]
	assert chances == sorted(chances), "an open stage further on is not less likely"


def test_every_outcome_the_field_offers_is_handled():
	field = json.loads((tree.APP / "one_crm" / "custom" / "sales_stage.json").read_text())["custom_fields"]
	options = next(one["options"] for one in field if one["fieldname"] == "one_outcome").split("\n")
	space = _module()
	assert set(options) - {"Open", space["HOLD"]} == set(space["STATUS"]) == set(space["CLOSED"])


def test_every_way_a_status_changes_is_hooked():
	assert '"onedesk.one_crm.stages.before_validate"' in HOOKS
	for doctype in ("Quotation", "Sales Order"):
		assert f'"{doctype}": {{\n\t\t"on_submit": "onedesk.one_crm.stages.follow"' in HOOKS
	assert '"onedesk.one_crm.stages.settle"' in HOOKS
	assert '"Opportunity-sales_stage"' in HOOKS, "stage history comes from the Milestone Tracker fixture"


# ------------------------------------------------------------------ the board

BOARD = tree.APP / "one_crm" / "board.py"


def _totals():
	space = {"flt": lambda value: float(value or 0)}
	for node in ast.parse(BOARD.read_text(encoding="utf-8")).body:
		if isinstance(node, ast.FunctionDef) and node.name == "totals":
			exec(ast.unparse(node), space)
	return space["totals"]


def test_a_column_is_worth_its_deals_and_their_weighted_value():
	totals = _totals()
	got = totals(
		[
			{"sales_stage": "Proposal", "base_opportunity_amount": 50000, "probability": 50},
			{"sales_stage": "Proposal", "base_opportunity_amount": 8000, "probability": 50},
			{"sales_stage": "New", "base_opportunity_amount": 0, "base_total": 1200, "probability": 10},
		]
	)
	assert got["Proposal"] == {"value": 58000, "weighted": 29000}
	assert got["New"] == {"value": 1200, "weighted": 120}, "a deal priced by its items is worth its items"


def test_the_board_follows_the_stages_and_keeps_lost_off_it():
	source = BOARD.read_text(encoding="utf-8")
	assert '"Archived" if stage.one_outcome == "Lost"' in source, "a drop cannot say why a deal was lost"
	for event in ("on_update", "after_rename", "after_delete"):
		assert f'"{event}": "onedesk.one_crm.board.sync"' in HOOKS
	assert '"onedesk.one_crm.board.sync"' in HOOKS.split("after_migrate")[1].split("]")[0]


def test_a_deal_is_called_a_deal_in_every_shipped_language():
	rows = json.loads((tree.APP / "fixtures" / "translation.json").read_text(encoding="utf-8"))
	said = {(row["language"], row["source_text"]): row["translated_text"] for row in rows}
	for lang in ("en", "ar", "de"):
		assert said.get((lang, "Opportunity")), f"{lang} still says Opportunity"
	sources = {source for _lang, source in said}
	for lang in ("en", "ar", "de"):
		assert {source for language, source in said if language == lang} == sources, f"{lang} is missing a word"
	assert all(row["name"].startswith("one-deal-") for row in rows), "the fixture filter is by name"


def test_a_deal_on_hold_is_open_and_out_of_the_pipeline():
	"""On Hold changes no status and never reopens or moves a deal by itself:
	only a closed outcome does that. The pipeline's figures leave it out."""
	source = STAGES.read_text(encoding="utf-8")
	assert '_outcome(doc.sales_stage) != "Open"' not in source
	assert 'now != "Open"' not in source
	assert source.count("in CLOSED") >= 3
	measure = (tree.APP / "one_crm" / "measure.py").read_text()
	assert measure.count("deals(alive())") == 2 and "stages.held()" in measure
	forecast = (tree.APP / "one_crm" / "report" / "deal_forecast" / "deal_forecast.py").read_text()
	assert "measure.alive()" in forecast


def test_a_workspace_seeded_before_on_hold_is_given_it_once():
	patches = (tree.APP / "patches.txt").read_text()
	assert "onedesk.one_crm.patches.add_on_hold" in patches.split("[post_fixture_sync]", 1)[1]
