"""Intake, stage 11: paying from the document, explaining it, the tax year's
bundle, keeping periods, and a delivery nobody ordered. Pure."""

import ast
import calendar as _calendar
import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "onedesk" / "one_intake"


def _load(path, space, names=None):
	for node in ast.parse(path.read_text()).body:
		if isinstance(node, (ast.Import, ast.ImportFrom)):
			continue
		named = getattr(node, "name", None) or (getattr(node.targets[0], "id", None) if isinstance(node, ast.Assign) else None)
		if names is None or named in names:
			exec(ast.unparse(node), space)
	return space


PAY = _load(ROOT / "pay.py", {}, {"MOST", "epc"})
EXPLAIN = _load(ROOT / "explain.py", {"json": json}, {"MOST_TEXT", "shaped", "prompt"})
KEEP = _load(ROOT / "keep.py", {"date": date}, {"PERIODS", "period", "until"})
BUNDLE = _load(ROOT / "bundle.py", {"re": re}, {"KINDS", "safe", "unique"})
ACT = _load(ROOT / "act.py", {"dataclass": dataclass, "field": field, "hashlib": hashlib, "json": json, "cint": lambda v: int(v or 0), "flt": lambda v, p=None: float(v or 0)}, {"KINDS", "FLOOR", "CHANGES", "Action"})
MONEY = _load(ROOT / "money.py", {"_Action": ACT["Action"]})


def test_a_girocode_is_the_epc_text_and_nothing_else():
	text = PAY["epc"]("Stadtwerke Köln GmbH", "DE02 1203 0000 0000 2020 51", 84.2, "RE-2026-1001")
	assert text.split("\n") == ["BCD", "002", "1", "SCT", "", "Stadtwerke Köln GmbH", "DE02120300000000202051", "EUR84.20", "", "", "RE-2026-1001"]
	creditor = PAY["epc"]("A", "DE02120300000000202051", 10, "RF18 5390 0754 7034")
	assert creditor.split("\n")[9] == "RF18539007547034" and len(creditor.split("\n")) == 10, "a creditor reference is structured, never both"
	assert PAY["epc"]("A", "", 10) is None and PAY["epc"]("", "DE02120300000000202051", 10) is None
	assert PAY["epc"]("A", "DE02120300000000202051", 0) is None, "nothing to pay is no code"
	assert PAY["epc"]("A", "DE02120300000000202051", None).split("\n")[-1] == "DE02120300000000202051", "no amount lets the payer type it"


def test_an_explanation_is_cut_to_what_the_panel_draws():
	said = EXPLAIN["shaped"]({"explanation": "x" * 5000, "todo": [{"what": "Pay", "by": "2026-10-01"}, "junk", {"by": "2026-10-02"}], "reply": "Sehr geehrte", "reply_language": "de"})
	assert len(said["explanation"]) == 3000
	assert said["todo"] == [{"what": "Pay", "by": "2026-10-01"}]
	assert said["reply"] == "Sehr geehrte" and said["reply_language"] == "de"


def test_the_cancellation_asks_for_the_last_day_and_the_model_never_counts():
	doc = {"kind": "Contract", "text": "Vertrag", "notice_period": "drei Monate", "dates": [{"date": date(2026, 12, 31), "what": "Valid Until"}]}
	asked = EXPLAIN["prompt"](doc, "ar", "cancel", "2026-09-30")
	assert "must arrive by 2026-09-30" in asked and "The reader's language: ar." in asked
	assert "2026-12-31" in asked and asked.endswith("Vertrag")
	assert "Write a short reply" in EXPLAIN["prompt"](doc, "en", "explain", None)


def test_a_business_keeps_its_papers_for_the_years_its_country_says():
	assert KEEP["period"]("Invoice", "DE") == (8, "§ 147 AO")
	assert KEEP["period"]("Delivery Note", "de") == (6, "§ 257 HGB")
	assert KEEP["until"]("Invoice", "DE", date(2026, 3, 1)) == date(2034, 12, 31), "from the end of the year it is dated in"
	assert KEEP["until"]("Invoice", "AE", date(2026, 3, 1)) == date(2031, 12, 31)
	assert KEEP["until"]("Sick Note", "DE", date(2026, 3, 1)) is None
	assert KEEP["until"]("Invoice", "FR", date(2026, 3, 1)) is None, "a country not listed keeps nothing by us"


def test_the_bundle_names_files_every_system_accepts_and_never_twice():
	assert BUNDLE["safe"]('Rechnung: 08/2026 "Strom"?') == "Rechnung 08 2026 Strom"
	assert BUNDLE["safe"]("") == "document"
	taken = set()
	assert BUNDLE["unique"]("2026/Invoice/a.pdf", taken) == "2026/Invoice/a.pdf"
	assert BUNDLE["unique"]("2026/Invoice/a.pdf", taken) == "2026/Invoice/a (2).pdf"
	assert BUNDLE["unique"]("2026/Invoice/scan", taken) == "2026/Invoice/scan"
	assert BUNDLE["unique"]("2026/Invoice/scan", taken) == "2026/Invoice/scan (2)"
	assert "Payslip" in BUNDLE["KINDS"] and "CV" not in BUNDLE["KINDS"]


def test_a_delivery_nobody_ordered_is_a_task_to_check_it():
	said = {"unordered": "Check the delivery from {0}", "see_document": "See the document."}
	ctx = {"books": True, "today": "2026-09-24", "said": said, "supplier": "Bonner Druck KG", "person": "boss@acme.test"}
	note = {"kind": "Delivery Note", "verdict": "Action", "number": "LS-1"}
	made = MONEY["unordered"](note, ctx)
	assert len(made) == 1 and made[0].doctype == "Task" and "Bonner Druck KG" in made[0].values["subject"]
	assert MONEY["unordered"](note, {**ctx, "purchase_order": "PUR-ORD-1"}) == []
	assert MONEY["unordered"](note, {**ctx, "supplier": None}) == [], "an unknown sender is not ours to chase"
	assert MONEY["unordered"]({**note, "change": "Nudge"}, ctx) == []


AUDIT = _load(ROOT / "audit.py", {"json": json}, {"MOST_TEXT", "FILING", "VERDICTS", "worth", "held", "shown", "prompt", "verdicts"})


def test_the_auditor_is_asked_only_where_there_is_something_to_get_wrong():
	filed = [{"name": "a", "kind": "Move", "level": "Done"}, {"name": "b", "kind": "Tag", "level": "Done"}]
	assert not AUDIT["worth"](filed), "filing alone is not worth a call"
	assert AUDIT["worth"](filed + [{"name": "c", "kind": "Create", "level": "Done"}])
	assert AUDIT["worth"]([{"name": "d", "kind": "Link", "level": "Proposed"}])


def test_the_auditor_never_ends_somebodys_employment():
	assert AUDIT["held"]({"target_doctype": "Employee", "after": json.dumps({"relieving_date": "2026-12-31"})})
	assert not AUDIT["held"]({"target_doctype": "Employee", "after": json.dumps({"cell_number": "+49"})})


def test_the_auditors_answer_is_one_clean_verdict_per_action_it_was_shown():
	said = {"actions": [{"id": "a", "verdict": "RIGHT", "why": "It says so."}, {"id": "b", "verdict": "maybe"}, {"id": "zzz", "verdict": "right"}, "junk"]}
	found = AUDIT["verdicts"](said, {"a", "b", "c"})
	assert found == {"a": {"verdict": "right", "why": "It says so."}, "b": {"verdict": "unsure", "why": ""}}, "an action it was not shown is ignored"
	assert AUDIT["verdicts"](None, {"a"}) == {}


def test_the_auditor_sees_the_document_and_what_was_done_with_it():
	row = {"name": "a", "kind": "Create", "level": "Proposed", "target_doctype": "Purchase Invoice", "target_name": None, "after": json.dumps({"supplier": "X"}), "before": None, "why": "Not sure."}
	shown = AUDIT["shown"](row)
	assert shown["state"] == "waiting for approval" and shown["record"] == "Purchase Invoice (new)" and shown["values"] == {"supplier": "X"}
	asked = AUDIT["prompt"]({"kind": "Invoice", "text": "Rechnung", "dropped": "tax 1 is not in the document", "parties": []}, [shown])
	assert "tax 1 is not in the document" in asked and asked.endswith("Rechnung") and '"id": "a"' in asked
