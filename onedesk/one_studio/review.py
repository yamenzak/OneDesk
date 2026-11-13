"""The second reading: does an extension's code do what it says, and nothing
else? A separate AI action (`studio_review`) that sees nothing of the chat.
"""

import json

import frappe
from frappe.utils import sha256_hash

REVIEW = "studio_review"

VERDICTS = ("Pass", "Refuse")

MOST_CODE = 20_000


def fingerprint(code: str, runs: str, doctype: str, when: str) -> str:
	"""What the review was of: the code, and where and when it runs. The guard
	and the reviewer read the code for one kind of record at one moment, so a
	change to any of the four needs a new review. Pure."""
	of = json.dumps([code or "", runs or "", doctype or "", when or ""], ensure_ascii=False)
	return sha256_hash(of)


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
