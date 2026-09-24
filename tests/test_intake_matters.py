"""Intake, stage 5: which matter a document belongs to, and what it changes."""

import ast
import re
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "onedesk" / "one_intake"


def _flt(value, precision=None):
	try:
		return float(value if value is not None else 0)
	except (TypeError, ValueError):
		return 0.0


def _getdate(value):
	return value if isinstance(value, date) else date.fromisoformat(str(value)[:10])


SPACE = {"re": re, "flt": _flt, "getdate": _getdate, "timedelta": timedelta}
for node in ast.parse((ROOT / "matters.py").read_text()).body:
	named = getattr(node, "name", None) or (getattr(node.targets[0], "id", None) if isinstance(node, ast.Assign) else None)
	if named in {"FOLLOWERS", "CHANGES", "compact", "is_copy", "by_reference", "by_party", "change_of", "urgent"}:
		exec(ast.unparse(node), SPACE)

STADTWERKE = ("Supplier", "Stadtwerke Köln GmbH")
INVOICE = {"name": "r1", "kind": "Invoice", "number": "RE-2026-0042", "gross": 84.2, "issued_on": "2026-09-01", "party": STADTWERKE, "refs": ["PO-7"]}


def test_a_copy_is_the_same_document_from_the_same_party():
	is_copy = SPACE["is_copy"]
	assert is_copy({**INVOICE, "name": "r2", "number": "RE 2026 0042"}, INVOICE), "spacing is not a difference"
	assert is_copy({**INVOICE, "gross": 84.20000001}, INVOICE)
	assert not is_copy({**INVOICE, "gross": 94.2}, INVOICE), "a corrected amount is an update, not a copy"
	assert not is_copy({**INVOICE, "party": ("Supplier", "Other")}, INVOICE), "4711 is somebody else's invoice too"
	assert not is_copy({**INVOICE, "kind": "Reminder"}, INVOICE)
	assert not is_copy({**INVOICE, "number": None}, INVOICE), "nothing to compare is no copy"
	assert not is_copy({**INVOICE, "party": None}, INVOICE), "the same number from a new issuer is a new document"


def test_a_reference_places_a_document_with_the_one_it_names():
	by_reference = SPACE["by_reference"]
	reminder = {"kind": "Reminder", "refs": ["RE-2026-0042"], "party": None}
	assert by_reference(reminder, [INVOICE])["name"] == "r1", "a reminder with no party known is placed by the number"
	assert by_reference({**reminder, "party": ("Supplier", "Other")}, [INVOICE]) is None
	assert by_reference({"refs": ["PO-7"], "party": STADTWERKE}, [INVOICE])["name"] == "r1", "a reference the invoice carried"
	assert by_reference({"refs": ["12"]}, [{**INVOICE, "number": "12"}]) is None, "too short to mean anything"
	september = {"kind": "Invoice", "number": "RE-2026-0901", "refs": ["PO-7"], "party": STADTWERKE}
	assert by_reference(september, [INVOICE]) is None, "next month's invoice on the same order is its own matter"


def test_the_party_places_a_follower_only_when_it_is_sure():
	by_party = SPACE["by_party"]
	reminder = {"kind": "Reminder", "party": STADTWERKE}
	assert by_party(reminder, [INVOICE])["name"] == "r1"
	assert by_party(reminder, [INVOICE, {**INVOICE, "name": "r3"}]) is None, "two open invoices: not sure"
	assert by_party({"kind": "Letter", "party": STADTWERKE}, [INVOICE]) is None, "a letter does not follow an invoice"
	assert by_party({"kind": "Reminder", "party": None}, [INVOICE]) is None
	assert by_party({"kind": "Invoice", "number": "RE-2026-0903", "party": STADTWERKE}, [INVOICE]) is None, "a new invoice is its own matter"


def test_what_a_document_changes_is_read_from_its_facts():
	change_of = SPACE["change_of"]
	assert change_of({"kind": "Invoice"}, None) == "New"
	assert change_of({"kind": "Reminder"}, INVOICE) == "Nudge"
	assert change_of({"kind": "Payment Advice"}, INVOICE) == "Closing"
	assert change_of({"kind": "Invoice", "number": "RE-2026-0042", "gross": 94.2}, INVOICE) == "Update", "a corrected invoice"
	assert change_of({"kind": "Invoice", "number": "RE-2026-0042", "gross": 84.2}, INVOICE) == "Nothing New"
	assert change_of({"kind": "Letter"}, INVOICE, automatic=True) == "Nothing New", "an out-of-office"
	assert change_of({"kind": "Delivery Note"}, {"kind": "Order"}) == "Answer"
	assert change_of({"kind": "Letter"}, INVOICE) is None, "only reading it can tell"


def test_money_and_deadlines_due_within_a_day_do_not_wait():
	urgent = SPACE["urgent"]
	assert urgent([{"what": "Due", "date": "2026-09-25"}], "2026-09-24")
	assert not urgent([{"what": "Due", "date": "2026-10-30"}], "2026-09-24")
	assert not urgent([{"what": "Appointment", "date": "2026-09-24"}], "2026-09-24")
	assert urgent([], "2026-09-24", "Phishing")


def test_references_are_compared_the_way_they_are_stored():
	facts = (ROOT / "facts.py").read_text()
	assert 're.sub(r"[^0-9a-z]", "", str(value or "").lower())' in facts
	assert SPACE["compact"]("RE-2026/0042") == "re20260042"


def test_acting_waits_for_quiet_and_lessons_turn_into_asking():
	hooks = (ROOT.parent / "hooks.py").read_text()
	assert "onedesk.one_intake.matters.due" in hooks
	assert hooks.count('"* * * * *"') == 1, "a second key of the same cron line would silently replace the first"
	assert '"onedesk.one_intake.lessons.deleted",\n\t\t\t"onedesk.one_ai.touch.forget"' in hooks, "the lesson is read before the mark goes"
	assert "ignore_links_on_delete" in hooks
	source = (ROOT / "act.py").read_text()
	assert "lessons.rule_says(reading, action)" in source and 'lessons.learn(row, "Dismissed")' in source and 'lessons.learn(row, "Undone")' in source


def test_understood_documents_are_still_found_and_only_by_those_who_may_open_them():
	source = (ROOT / "search.py").read_text()
	assert source.count("state in ('Read', 'Understood')") >= 2, "understanding a document must not hide it from search"
	body = source[source.index("def find_documents("):]
	assert "files_of(" in body and "messages_of(" in body, "every hit is checked against the file or the message"
	hooks = (ROOT.parent / "hooks.py").read_text()
	assert '"onedesk.one_intake.search.find_documents"' in hooks
	memory = (ROOT.parent / "one_ai" / "memory.py").read_text()
	assert "search.about(doctype, name)" in memory
