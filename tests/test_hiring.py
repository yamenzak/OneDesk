"""OneAI on the hiring walk: read, rated and placed, and never decided.

See `one_hr/README.md`, under Hiring. What this keeps: the model's answer is read however it
is wrapped; the pool is shown under labels and a label the model made up
reaches no record; nothing here writes an applicant's status or the rating a
person gives; every job runs as OneAI; and the instruction says what a CV may
not be judged on.
"""

import ast
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

HIRING = tree.APP / "one_hr" / "hiring.py"
FIXTURE = tree.APP / "fixtures" / "ai_action.json"


def _pure(*names):
	"""These functions, run on their own: they touch nothing but their arguments."""
	space = {"re": re, "json": json}
	tree_ = ast.parse(HIRING.read_text(encoding="utf-8"))
	for node in tree_.body:
		if isinstance(node, ast.FunctionDef) and node.name in names:
			exec(ast.unparse(node), space)
	return space


def test_an_answer_is_read_however_it_is_wrapped():
	read = _pure("read")["read"]
	assert read('```json\n{"rating": 4}\n```') == {"rating": 4}
	assert read('Here you go: {"rating": 2, "brief": "x"} Hope that helps.') == {"rating": 2, "brief": "x"}
	assert read("I could not read the CV.") is None
	assert read("") is None
	assert read("{not json}") is None


def test_labels_become_applicants_and_invented_ones_are_dropped():
	unaliased = _pure("unaliased")["unaliased"]
	aliases = {"A1": ("ziad@x.com", "Ziad Mansour"), "NEW": ("layla@x.com", "Layla Nasser")}
	out = unaliased(
		{
			"standing": {"NEW": 88, "A1": 46, "A9": 99},
			"why_moved": {"A1": "NEW has the infrastructure work; A1 does not.", "A9": "made up"},
			"brief": "Stronger than A1 on roads.",
		},
		aliases,
	)
	assert out["standing"] == {"layla@x.com": 88, "ziad@x.com": 46}
	assert out["why_moved"] == {"ziad@x.com": "Layla Nasser has the infrastructure work; Ziad Mansour does not."}
	assert out["brief"] == "Stronger than Ziad Mansour on roads."


def test_a_standing_is_kept_to_the_pool_and_to_a_hundred():
	space = _pure("standings", "_clamped")
	out = space["standings"]({"standing": {"a": 140, "b": -3, "c": "71.26", "d": "high", "e": 50}}, {"a", "b", "c", "d"})
	assert out == {"a": 100, "b": 0, "c": 71.3}


def test_the_pool_is_shown_under_labels_never_ids():
	"""HRMS names an applicant after their email, so an id is a name."""
	said = ast.unparse(next(n for n in ast.parse(HIRING.read_text()).body if getattr(n, "name", "") == "_pool_said"))
	assert "A{at}" in said
	assert "one.name" not in said and "applicant_name" not in said


def test_nothing_here_decides_for_a_person():
	"""No status is set and the rating a person gives is never written."""
	source = HIRING.read_text(encoding="utf-8")
	assert not re.search(r'set_value\(\s*"Job Applicant"[^)]*"status"', source)
	assert not re.search(r'"Job Applicant"[^\n]*\.status\s*=', source)
	assert "applicant_rating" not in source


def test_every_job_runs_as_oneai():
	source = ast.parse(HIRING.read_text(encoding="utf-8"))
	for node in source.body:
		if isinstance(node, ast.FunctionDef) and node.name in ("screen", "rank"):
			assert "frappe.set_user(AUTHOR)" in ast.unparse(node), node.name


def test_the_hiring_instructions_say_what_may_not_be_judged():
	rows = {row["name"]: row for row in json.loads(FIXTURE.read_text(encoding="utf-8"))}
	for key in ("screen", "interview"):
		said = rows[key]["instruction"].lower()
		for word in ("age", "gender", "religion", "nationality", "disability", "photograph", "name implies"):
			assert word in said, f"{key} does not rule out {word}"
		assert rows[key]["may_use_tools"] == 0
	assert rows["transcribe"]["capability"] == "Transcription"
	assert "never write a name" in rows["transcribe"]["instruction"].lower()


def test_a_new_applicant_is_screened_after_commit():
	hooks = (tree.APP / "hooks.py").read_text(encoding="utf-8")
	assert re.search(r'"Job Applicant": \{"after_insert": \[?"onedesk\.one_hr\.hiring\.arrived"', hooks)
	source = HIRING.read_text(encoding="utf-8")
	assert "enqueue_after_commit=True" in source


def test_a_transcript_is_timed_from_the_start_of_the_interview():
	space = _pure("clock")
	space["cint"] = int
	exec("", space)
	clock = space["clock"]
	assert clock(0) == "00:00"
	assert clock(305) == "05:05"
	assert clock(3725) == "1:02:05"


def test_nothing_is_recorded_without_the_candidates_agreement():
	source = HIRING.read_text(encoding="utf-8")
	start = ast.unparse(next(n for n in ast.parse(source).body if getattr(n, "name", "") == "start_recording"))
	assert "if not cint(agreed)" in start and "frappe.throw" in start
	assert "'agreed_by': frappe.session.user" in start
	record = (tree.APP / "one_hr" / "doctype" / "interview_recording" / "interview_recording.py").read_text()
	assert "if not self.agreed" in record, "a recording made any other way must still carry the agreement"


def test_only_retention_or_an_hr_manager_deletes_what_was_said():
	hooks = (tree.APP / "hooks.py").read_text(encoding="utf-8")
	assert '"onedesk.one_hr.hiring.keep_sound",' in hooks.split('"File": {', 1)[1].split("}", 1)[0]
	assert '"onedesk.one_hr.hiring.purge"' in hooks
	spec = json.loads((tree.APP / "one_hr" / "doctype" / "interview_recording" / "interview_recording.json").read_text())
	deleting = [row["role"] for row in spec["permissions"] if row.get("delete")]
	assert deleting == ["HR Manager"]


def test_feedback_is_only_ever_drafted_for_one_of_the_interviewers():
	ai = (tree.APP / "one_hr" / "ai.py").read_text(encoding="utf-8")
	draft = ast.unparse(next(n for n in ast.parse(ai).body if getattr(n, "name", "") == "draft_interview_feedback"))
	assert "me not in on_it" in draft
	assert "'interviewer': me" in draft
