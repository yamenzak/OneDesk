"""Reading, the first look: Clef sorts what arrives, and the talk model looks
only when Clef can't (docs/AICENTER.md, Reading what arrives)."""

import ast
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from onedesk.one_ai import jobs

NAMES = (
	"DECIDE", "VERDICTS", "CRITERIA", "WANTS", "JUNK", "ABOUT", "questions", "decided", "about_of",
	"EXTRACT", "TWICE", "FIELDS", "TAKEN", "DISAGREE", "compared", "_same",
)  # fmt: skip


def _understand():
	"""understand.py's pure parts, without a site."""
	space = {"flt": lambda value, default=0.0: float(value) if value not in (None, "") else default}
	source = (Path(__file__).resolve().parent.parent / "onedesk" / "one_ai" / "reading" / "understand.py").read_text()
	for node in ast.parse(source).body:
		named = getattr(node.targets[0], "id", "") if isinstance(node, ast.Assign) else getattr(node, "name", "")
		if named in NAMES:
			exec(ast.unparse(node), space)
	return SimpleNamespace(**{name: space[name] for name in NAMES})


understand = _understand()

TOPICS = [("rule-1", "a complaint about a delivery"), ("rule-2", "a quote request")]


def test_clef_is_asked_what_it_is_whether_it_asks_and_each_topic():
	asked = understand.questions(TOPICS)
	assert set(asked) == {"what", "asks", "t1", "t2"}
	assert asked["what"]["type"] == "choice" and "Real" in asked["what"]["criteria"]
	assert set(asked["what"]["criteria"]) - {"Real"} <= set(understand.VERDICTS)
	assert asked["what"]["instructions"] == jobs.words(understand.DECIDE)
	assert asked["asks"]["type"] == "noul" and asked["t2"]["type"] == "noul" and "a quote request" in asked["t2"]["instructions"]
	assert jobs.JOBS[understand.DECIDE].kind == "decide"


def test_something_real_is_action_when_it_asks_and_information_when_not():
	bill = {"what": {"choice": "Real"}, "asks": {"noul": 0.93}}
	note = {"what": {"choice": "Real"}, "asks": {"noul": 0.1}}
	assert understand.decided(bill, [])[0] == "Action" and understand.decided(note, [])[0] == "Information"
	assert understand.decided({"what": {"choice": "Newsletter"}}, [])[0] == "Newsletter"


def test_junk_is_left_to_the_talk_model():
	"""Clef took real payment reminders for phishing when measured."""
	for junk in understand.JUNK:
		assert understand.decided({"what": {"choice": junk, "probabilities": {junk: 0.99}}}, TOPICS) == (None, [])


def test_topics_are_the_ones_clef_finds_likely():
	said = {"what": {"choice": "Real"}, "asks": {"noul": 0.8}, "t1": {"noul": 0.81}, "t2": {"noul": 0.2}}
	verdict, numbers = understand.decided(said, TOPICS)
	assert verdict == "Action" and numbers == [1]
	assert understand.about_of(numbers, TOPICS) == {"rule-1"}


def test_an_answer_clef_did_not_give_falls_back_to_the_talk_model():
	assert understand.decided({}, TOPICS) == (None, [])
	assert understand.decided({"what": {"choice": "Maybe"}}, TOPICS) == (None, [])


BILL = {"kind": "Invoice", "number": "NW-48213", "issued": "2026-10-14", "money": {"gross": 3780.0, "currency": "USD"}, "confidence": 0.9}


def test_a_bill_read_twice_alike_stands():
	same = {"number": {"value": "NW 48213".replace(" ", "-"), "confidence": 0.99}, "gross": {"value": 3780, "confidence": 0.99}, "issued": {"value": "2026-10-14", "confidence": 0.95}}
	said = understand.compared(BILL, same)
	assert said["confidence"] == 0.9 and "read_twice" not in said


def test_a_bill_read_twice_differently_waits_for_a_person():
	other = {"gross": {"value": 3870, "confidence": 0.99}}
	said = understand.compared(BILL, other)
	assert said["confidence"] == understand.DISAGREE and said["read_twice"] == ["gross"]
	assert understand.compared(BILL, {"gross": {"value": 3870, "confidence": 0.5}})["confidence"] == 0.9, "an unsure second read changes nothing"


def test_the_second_read_fills_what_the_first_left_empty():
	empty = {**BILL, "number": None, "money": {"currency": "USD"}}
	said = understand.compared(empty, {"number": {"value": "NW-48213", "confidence": 0.99}, "gross": {"value": 3780, "confidence": 0.97}})
	assert said["number"] == "NW-48213" and said["money"]["gross"] == 3780.0 and said["money"]["currency"] == "USD"
	assert set(understand.FIELDS) == {"number", "issued", "gross"} and "Invoice" in understand.TWICE
