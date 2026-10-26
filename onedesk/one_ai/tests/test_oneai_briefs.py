"""OneAI's summary at the top of a customer, supplier, opportunity and project.

Every record type that carries one has its three fields, every record type
that marks one due names one that carries one, the hooks call it on save,
submit and cancel, and it runs hourly. A summary is a field shown in the head,
never a comment.
"""

import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

import tree

BRIEF = tree.APP / "one_ai" / "brief.py"


def _constant(name: str):
	for node in ast.parse(BRIEF.read_text(encoding="utf-8")).body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", None) == name:
			return node.value
	raise AssertionError(f"{name} is not in brief.py")


def _briefs() -> tuple:
	return ast.literal_eval(_constant("BRIEFS"))


def test_every_record_that_carries_one_has_its_fields():
	for doctype in _briefs():
		held = json.loads((tree.APP / "one_ai" / "custom" / f"{doctype.lower()}.json").read_text(encoding="utf-8"))
		fields = {one["fieldname"]: one for one in held["custom_fields"] if one["fieldname"].startswith("one_ai_brief")}
		assert {"one_ai_brief", "one_ai_brief_on", "one_ai_brief_due"} <= set(fields), doctype
		assert all(one.get("hidden") and one.get("read_only") and one.get("no_copy") for one in fields.values()), doctype


def test_what_marks_one_due_names_a_record_that_carries_one():
	watched = _constant("WATCHED")
	briefs = set(_briefs())
	for key, value in zip(watched.keys, watched.values, strict=True):
		if isinstance(value, ast.Dict):
			named = {ast.literal_eval(one) for one in value.keys}
			assert named <= briefs, f"{ast.literal_eval(key)} marks {named - briefs}"


def test_it_is_wired_to_every_save_submit_and_cancel_and_runs_hourly():
	hooks = (tree.APP / "hooks.py").read_text(encoding="utf-8")
	star = hooks[hooks.index('\t"*": {') :]
	star = star[: star.index("\n\t},")]
	for event in ("on_update", "on_submit", "on_cancel"):
		block = star[star.index(f'"{event}": [') :]
		assert "onedesk.one_ai.brief.touched" in block[: block.index("]")], event
	hourly = hooks[hooks.index('"hourly": [') :]
	assert "onedesk.one_ai.brief.due" in hourly[: hourly.index("]")]
	assert 'one_record_notices = ["onedesk.one_ai.heads.NOTICES"]' in hooks


def test_a_draft_saved_is_not_news_and_a_summary_is_never_a_comment():
	source = BRIEF.read_text(encoding="utf-8")
	touched = source[source.index("def touched(") : source.index("def due(")]
	assert 'method == "on_update" and doc.meta.is_submittable' in touched
	assert '"Comment"' not in source[source.index("def write(") : source.index("def asked(")]


def test_it_is_written_at_most_once_a_day():
	source = BRIEF.read_text(encoding="utf-8")
	due = source[source.index("def due(") : source.index("def later(")]
	assert "add_days(now_datetime(), -DAY)" in due and "is null or" in due
	assert "account.configured()" in due
