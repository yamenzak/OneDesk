"""A workspace picks models for a few jobs, not for two dozen actions.

Every action belongs to exactly one job, so nothing is left without a place
to choose its model; a job's model reaches only the actions that can run on
it; and the account offers a search model by itself when nobody chose one.
"""

import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree


def _jobs() -> tuple:
	body = ast.parse((tree.APP / "one" / "settings.py").read_text(encoding="utf-8"))
	node = next(
		one for one in body.body if isinstance(one, ast.Assign) and getattr(one.targets[0], "id", None) == "JOBS"
	)
	room = {"_lt": lambda text, **_: text}
	exec(compile(ast.Module(body=[node], type_ignores=[]), "settings.py", "exec"), room)
	return room["JOBS"]


def _actions() -> list[dict]:
	return json.loads((tree.APP / "fixtures" / "ai_action.json").read_text(encoding="utf-8"))


def test_every_action_is_in_exactly_one_job():
	held = [action for job in _jobs() for action in job["actions"]]
	shipped = {one["name"] for one in _actions()}
	assert len(held) == len(set(held)), "an action is in two jobs"
	assert shipped - set(held) == set(), f"no job chooses a model for {sorted(shipped - set(held))}"
	assert set(held) - shipped == set(), f"a job names an action that is not shipped: {sorted(set(held) - shipped)}"


def test_a_job_needs_what_most_of_its_actions_are():
	capability = {one["name"]: one["capability"] for one in _actions()}
	for job in _jobs():
		assert any(capability[action] == job["needs"] for action in job["actions"]), job["key"]


def test_a_job_model_reaches_only_the_actions_that_can_run_on_it():
	run = (tree.APP / "one_ai" / "run.py").read_text(encoding="utf-8")
	body = run[run.index("def set_job(") : run.index("def _told_job(")]
	assert '"capability": held["needs"]' in body
	assert "roles.require()" in body
	assert body.count("_told_job(") == 1, "the other administrators hear once, not once per action"


def test_the_account_offers_a_search_model_when_none_is():
	catalogue = (tree.APP / "one_admin" / "catalogue.py").read_text(encoding="utf-8")
	nightly = catalogue[catalogue.index("def nightly(") :]
	assert "searchable()" in nightly[: nightly.index("\ndef ")]
	body = catalogue[catalogue.index("def searchable(") :]
	body = body[: body.index("\ndef ")] if "\ndef " in body else body
	assert '"offered": 1' in body and "min(" in body and "input_per_million" in body
	assert '"default_for": "Embedding"' in body
