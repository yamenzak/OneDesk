"""The second reading: does an extension's code do what it says, and nothing
else?

OneAI writes an extension from what an administrator asked, so whoever asks
steers the writer. The reviewer is a separate call, its own AI action
(`studio_review`), shown the code, the explanation the administrator will
read, and where it runs, and nothing of the conversation, so nothing said
there reaches it. It answers Pass or Refuse with a reason. guard.py has
already refused what no explanation could excuse; this catches code that is
allowed but is not what it says: a check that also copies a field elsewhere,
a button that does more than its label.

An extension that has not passed, or whose code has changed since it passed,
cannot be turned on (extension.py).
"""

import hashlib
import json

import frappe

REVIEW = "studio_review"

VERDICTS = ("Pass", "Refuse")

#: What of the code the reviewer is shown, at most.
MOST_CODE = 20_000


def fingerprint(code: str) -> str:
	"""What the review was of: a change to the code needs a new one. Pure."""
	return hashlib.sha256((code or "").encode()).hexdigest()


def prompt(runs: str, doctype: str, when: str, explanation: str, code: str) -> str:
	"""What the reviewer is asked. Pure."""
	where = {"runs": runs, "record": doctype, "when": when}
	return (
		f"Where it runs: {json.dumps(where, ensure_ascii=False)}\n\n"
		f"What the administrator is told it does:\n{explanation or ''}\n\n"
		f"The code:\n{(code or '')[:MOST_CODE]}"
	)


def verdict(said: dict | None) -> dict:
	"""The reviewer's answer, clean; anything unreadable is a refusal. Pure."""
	said = said if isinstance(said, dict) else {}
	answer = str(said.get("verdict") or "").strip().title()
	why = str(said.get("why") or "").strip()[:500]
	if answer not in VERDICTS:
		return {"verdict": "Refuse", "why": why or "The review could not be read."}
	return {"verdict": answer, "why": why}


def ask(runs: str, doctype: str, when: str, explanation: str, code: str) -> dict:
	from onedesk.one_ai import run
	from onedesk.one_hr.hiring import read

	try:
		said = read(run.once(REVIEW, prompt(runs, doctype, when, explanation, code)))
	except Exception:
		frappe.log_error(title="OneStudio review")
		said = {"why": "The review could not be made just now. Ask OneAI to try again."}
	return verdict(said)
