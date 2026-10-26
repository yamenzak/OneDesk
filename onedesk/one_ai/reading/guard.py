"""Whether what arrived reads like an attack on OneAI, asked before OneAI
acts on it by itself (docs/AICENTER.md, Guardrails). Llama Guard reads the
text; one it calls unsafe, or a check that could not run, is left for a
person, and the reading says why."""

import frappe

JOB = "guard"

# The most of a reading the check is shown, in characters.
MOST = 12000

HELD = "it reads like instructions to OneAI, so OneAI left it for a person"


def unsafe(said: str | None) -> bool:
	"""Llama Guard's answer as a verdict: "safe", or "unsafe" and the
	categories. Anything else is not a pass. Pure."""
	return (said or "").split()[:1] != ["safe"]


def holds(reading, text: str) -> bool:
	"""Whether OneAI must not act on this reading by itself, and if so, the
	reading marked unsure with the reason."""
	from onedesk.one_ai import run

	try:
		held = unsafe(run.once(JOB, text[:MOST], reference=reading.name))
	except Exception:
		frappe.log_error(title=f"OneAI could not check {reading.name} before acting")
		held = True
	if held:
		dropped = [line for line in (reading.dropped or "").splitlines() if line and line != HELD]
		reading.db_set({"unsure": 1, "dropped": "\n".join([*dropped, HELD])})
	return held
