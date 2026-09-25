"""The auditor: a second agent that checks what OneAI did (docs/INTAKE.md §4).

Full automation means a person is asked only when a person is needed. The
reader that understood a document and planned what to do is not the one to
judge its own work, so once a document has been acted on, a separate call —
its own AI action, `intake_audit`, whose model a workspace chooses on its
own — is shown the document and everything done and proposed because of it,
and answers for each one whether it is right.

- **A proposal it finds right** is applied for the person it was read for,
  under their permission, and carries the OneAI mark like anything else OneAI
  made. **One it finds wrong** is dismissed. **One it is unsure of** waits.
- **Something done that it finds wrong** stays done and goes to the person's
  Waiting box with the auditor's reason, to undo or to keep. Undoing on the
  auditor's word alone would let one model's mistake erase another's work.
- It never decides what ends somebody's employment, and never retries what
  was refused for want of permission: those wait for a person whatever it says.

A document with nothing done but filing (moved, renamed, tagged, linked) and
nothing waiting is not audited: there is little to get wrong and a call to
pay for. A workspace can turn the auditor off in Intake Settings.
"""

import json

import frappe
from frappe.utils import cint

AUDIT = "intake_audit"

#: What of the document the auditor is shown.
MOST_TEXT = 12_000

#: What only files a document, which is not worth a call on its own.
FILING = ("Move", "Rename", "Tag", "Link")

VERDICTS = ("right", "wrong", "unsure")


def run(name: str) -> None:
	"""Audit one document's actions, once they are all made."""
	if not cint(frappe.db.get_single_value("Intake Settings", "audit")):
		return
	rows = frappe.get_all(
		"Intake Action",
		filters={"reading": name, "level": ["in", ("Done", "Proposed")], "audit": ["in", ("", None)]},
		fields=["name", "kind", "level", "target_doctype", "target_name", "why", "before", "after", "on_behalf_of", "flow"],
		order_by="creation asc",
	)
	if not worth(rows):
		return
	reading = frappe.get_doc("Reading", name)
	said = _ask(prompt(reading.as_dict(), [shown(row) for row in rows]))
	if not said:
		return
	decide(rows, said)


def worth(rows: list[dict]) -> bool:
	"""Whether a document's actions are worth a call: anything waiting, or
	anything done beyond filing it. Pure."""
	return any(row["level"] == "Proposed" or row["kind"] not in FILING for row in rows)


def held(row: dict) -> bool:
	"""What the auditor never decides for a person: ending somebody's
	employment. Pure."""
	after = row.get("after") or "{}"
	values = json.loads(after) if isinstance(after, str) else after
	return row.get("target_doctype") == "Employee" and bool({"relieving_date", "resignation_letter_date"} & set(values or {}))


def shown(row: dict) -> dict:
	"""One action as the auditor reads it. Pure."""
	after = json.loads(row.get("after") or "{}") if isinstance(row.get("after"), str) else (row.get("after") or {})
	before = json.loads(row.get("before") or "{}") if isinstance(row.get("before"), str) else (row.get("before") or {})
	return {
		"id": row["name"],
		"state": "done" if row["level"] == "Done" else "waiting for approval",
		"kind": row["kind"],
		"record": f"{row['target_doctype']} {row.get('target_name') or '(new)'}",
		"values": after,
		"was": before or None,
		"why_it_waits": row.get("why") if row["level"] == "Proposed" else None,
	}


def prompt(reading: dict, actions: list[dict]) -> str:
	"""What the auditor is asked. Pure."""
	facts = {
		"kind": reading.get("kind"),
		"title": reading.get("title"),
		"summary": reading.get("summary"),
		"number": reading.get("number"),
		"issued": str(reading.get("issued_on") or "") or None,
		"gross": reading.get("gross"),
		"currency": reading.get("currency"),
		"iban": reading.get("iban"),
		"parties": [{"role": one.get("role"), "name": one.get("party_name"), "matched": f"{one.get('matched_doctype') or ''} {one.get('matched_name') or ''}".strip() or None} for one in reading.get("parties") or []],
		"not_in_the_document": [line for line in (reading.get("dropped") or "").splitlines() if line],
	}
	return (
		f"What was read from it: {json.dumps(facts, ensure_ascii=False, default=str)}\n\n"
		f"What was done and proposed because of it: {json.dumps(actions, ensure_ascii=False, default=str)}\n\n"
		f"The document:\n{(reading.get('text') or '')[:MOST_TEXT]}"
	)


def verdicts(said: dict, ids: set) -> dict[str, dict]:
	"""The auditor's answer, one clean verdict per action it was shown. Pure."""
	out = {}
	for one in (said or {}).get("actions") or []:
		if not isinstance(one, dict) or one.get("id") not in ids:
			continue
		verdict = str(one.get("verdict") or "").lower()
		out[one["id"]] = {"verdict": verdict if verdict in VERDICTS else "unsure", "why": str(one.get("why") or "")[:500]}
	return out


def decide(rows: list[dict], said: dict) -> None:
	from onedesk.one_intake import act

	found = verdicts(said, {row["name"] for row in rows})
	for row in rows:
		verdict = found.get(row["name"]) or {"verdict": "unsure", "why": ""}
		audit = verdict["verdict"].title()
		if row["level"] == "Done" or held(row) or audit == "Unsure":
			frappe.db.set_value("Intake Action", row["name"], {"audit": audit, "audit_why": verdict["why"]}, update_modified=False)
			continue
		act.settle_for(frappe.get_doc("Intake Action", row["name"]), audit == "Right", verdict["why"])


def _ask(text: str) -> dict | None:
	from onedesk.one_ai import run
	from onedesk.one_hr.hiring import read

	try:
		return read(run.once(AUDIT, text))
	except Exception:
		frappe.log_error(title="Intake audit")
		return None
