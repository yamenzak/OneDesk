"""The check before reading acts by itself (docs/AICENTER.md, Guardrails):
Llama Guard's answer read as a verdict, and the agent asking it first."""

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree  # noqa: E402

GUARD = (tree.APP / "one_ai" / "reading" / "guard.py").read_text()
AGENT = (tree.APP / "one_ai" / "reading" / "agent.py").read_text()


def _unsafe():
	space = {}
	for node in ast.parse(GUARD).body:
		if getattr(node, "name", "") == "unsafe":
			exec(ast.unparse(node), space)
	return space["unsafe"]


def test_only_safe_passes():
	unsafe = _unsafe()
	assert not unsafe("\n\nsafe")
	assert unsafe("\n\nunsafe\nS6") and unsafe("unsafe\nS2,S7")
	assert unsafe("") and unsafe(None) and unsafe("I cannot tell"), "anything but safe is not a pass"


def test_the_agent_asks_before_it_acts_and_a_failed_check_holds():
	assert AGENT.index("guard.holds(reading, asked)") < AGENT.index("run.ask(")
	assert "held = True" in GUARD, "a check that could not run is not a pass"


def test_the_guard_is_told_nothing():
	sys.path.insert(0, str(tree.APP.parent))
	from onedesk.one_ai import jobs

	assert jobs.JOBS["guard"].kind == "guard" and jobs.told("guard") == ""
