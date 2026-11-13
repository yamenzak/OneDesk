"""Every action of every agent has a level (docs/ARC-AI.md, Trust and
permissions): each call an app's agent.py names in REACH and each tool in
TOOLS is Do it, Draft or Ask First in its LEVELS, with its words in
LABELS, and nothing else is."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from onedesk.one_ai.agents import levels  # noqa: E402


def test_every_action_of_an_agent_has_a_level():
	wrong = levels.every(ROOT / "onedesk")
	assert not wrong, wrong


def test_the_level_rule_catches_its_examples():
	good = 'REACH = {"leave.approve": "approve_leave"}\nNOT_FOR_AI = {"leave.pay": "Money."}\nTOOLS = ("read_leave",)\nLEVELS = {"leave.approve": "Ask First", "read_leave": "Do it"}\nLABELS = {"leave.approve": _lt("Approve Leave"), "read_leave": _lt("Read Leave")}\ndef read_leave():\n\tpass\n'
	assert levels.unlevelled(good) == []
	bad = 'REACH = {"leave.approve": "approve_leave", "leave.ask": "ask"}\nNOT_FOR_AI = {"leave.pay": "Money."}\nTOOLS = ("read_leave",)\nLEVELS = {"leave.approve": "Sometimes", "leave.pay": "Do it"}\nLABELS = {"leave.approve": _lt("Approve Leave"), "leave.pay": _lt("Pay")}\n'
	assert levels.unlevelled(bad) == [
		"leave.ask has no level",
		"read_leave has no level",
		"leave.approve's level 'Sometimes' is not one of ('Do it', 'Draft', 'Ask First')",
		"leave.pay has a level but is no action",
		"leave.pay is not for OneAI, so it has no level",
		"the tool read_leave is not in agent.py",
		"leave.ask has no label in LABELS",
		"read_leave has no label in LABELS",
		"leave.pay has a label but is no action",
	]
