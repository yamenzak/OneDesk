"""Intake, stage 3: a model's reading keeps only what the document says."""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from onedesk.one_intake import facts

LETTER = """Stadtwerke Köln GmbH · Parkgürtel 24 · 50823 Köln
Rechnung Nr. RE-2026-0042 vom 01.09.2026
Kundennummer 4711
Strom August 2026   250 kWh   70,76 €
Netto 70,76 € · USt 19 % 13,44 € · Gesamt 84,20 €
Bitte zahlen Sie bis 15. September 2026 auf DE89 3704 0044 0532 0130 00, Verwendungszweck KD 4711.
Ein Widerspruch ist innerhalb eines Monats möglich."""


def test_amounts_are_read_however_they_were_written():
	found = facts.amounts("Gesamt 1.234,56 € and total 1,234.56 USD and 84,20 and 12 items")
	assert {1234.56, 84.2, 12.0} <= found
	assert facts.number(84.2) == 84.2 and facts.number("84,20 €") == 84.2 and facts.number("1.234,56") == 1234.56
	assert facts.number("") is None and facts.number(None) is None


def test_dates_are_read_by_the_country_that_wrote_them():
	assert facts.parse_date("03.04.2026", "DE") == date(2026, 4, 3)
	assert facts.parse_date("03/04/2026", "DE") == date(2026, 4, 3)
	assert facts.parse_date("03/04/2026", "US") == date(2026, 3, 4), "month first in the US"
	assert facts.parse_date("3. April 2026") == date(2026, 4, 3)
	assert facts.parse_date("15. September 2026") == date(2026, 9, 15)
	assert facts.parse_date("September 15, 2026") == date(2026, 9, 15)
	assert facts.parse_date("2026-09-15") == date(2026, 9, 15)
	assert facts.parse_date("31.02.2026") is None, "no such day"
	assert date(2026, 9, 15) in facts.dates(LETTER) and date(2026, 9, 1) in facts.dates(LETTER)


def test_a_true_reading_passes_whole():
	reading = {
		"kind": "Invoice",
		"number": "RE-2026-0042",
		"issued": "2026-09-01",
		"money": {"net": 70.76, "tax": 13.44, "gross": 84.20, "iban": "DE89370400440532013000", "reference": "KD 4711", "currency": "EUR"},
		"lines": [{"text": "Strom August 2026", "amount": 70.76}],
		"dates": [{"date": "2026-09-15", "what": "due"}],
		"references": [{"kind": "customer", "value": "4711"}],
		"parties": [{"role": "sender", "name": "Stadtwerke Köln GmbH", "iban": "DE89 3704 0044 0532 0130 00"}],
	}
	checked, dropped = facts.check(reading, LETTER, "DE")
	assert dropped == []
	assert checked["money"]["gross"] == 84.2 and checked["dates"][0]["found"] == 1


def test_what_is_not_in_the_document_is_dropped_and_said():
	reading = {
		"number": "RE-2026-0043",
		"issued": "2026-09-02",
		"money": {"net": 70.76, "tax": 13.44, "gross": 94.20, "iban": "DE89370400440532013099"},
		"dates": [{"date": "2026-09-16", "what": "due"}, {"date": "2026-10-01", "what": "objection", "counted": True}],
		"parties": [{"name": "Stadtwerke", "vat_id": "DE999999999", "email": "fake@stadtwerke.example"}],
	}
	checked, dropped = facts.check(reading, LETTER, "DE")
	assert checked["money"]["gross"] is None and checked["money"]["iban"] is None
	assert checked["number"] is None and checked["issued"] is None
	assert [one["what"] for one in checked["dates"]] == ["objection"], "a counted deadline stays, marked not found"
	assert checked["dates"][0]["found"] == 0
	assert checked["parties"][0]["vat_id"] is None and checked["parties"][0]["email"] is None
	assert len(dropped) == 7


def test_totals_that_do_not_add_up_are_said():
	assert facts.totals_agree(70.76, 13.44, 84.20, [70.76])
	assert not facts.totals_agree(70.76, 13.44, 90.00)
	assert not facts.totals_agree(100.0, None, None, [40.0, 50.0])
	assert facts.totals_agree(None, None, 84.2, [84.2]), "a receipt with only a total"
	_checked, dropped = facts.check({"money": {"net": 70.76, "tax": 13.44, "gross": 84.20}, "lines": [{"amount": 13.44}]}, LETTER)
	assert "the totals do not add up" in dropped


def _understand(*names):
	import ast

	space = {}
	source = (Path(__file__).resolve().parent.parent / "onedesk" / "one_intake" / "understand.py").read_text()
	for node in ast.parse(source).body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") in names or isinstance(node, ast.FunctionDef) and node.name in names:
			exec(ast.unparse(node), space)
	return space


def test_an_e_invoice_is_understood_with_no_model():
	from onedesk.one_intake.readers import einvoice
	from test_intake_read import CII, UBL

	space = _understand("from_invoice", "_party")
	said = space["from_invoice"](einvoice.parse(UBL))
	assert said["kind"] == "Invoice" and said["number"] == "RE-2026-0042"
	assert said["money"]["gross"] == 84.2 and said["money"]["iban"] == "DE89370400440532013000"
	assert said["parties"][0]["role"] == "Sender" and said["parties"][0]["vat_id"] == "DE123456789"
	assert said["asks"] == [{"what": "Pay", "detail": "RE-2026-0042", "by": "2026-09-15"}]
	credit = space["from_invoice"](einvoice.parse(CII))
	assert credit["kind"] == "Credit Note" and credit["asks"] == [], "a credit note, debited, asks nobody to pay"


def test_a_kind_is_at_least_as_sensitive_as_it_is():
	sensitivity = _understand("SENSITIVE", "LEVELS", "sensitivity")["sensitivity"]
	assert sensitivity("Sick Note", "Ordinary") == "Medical", "the model cannot make a sick note ordinary"
	assert sensitivity("Invoice", "Legal") == "Legal"
	assert sensitivity("Payslip", None) == "Pay"
	assert sensitivity("Letter", "whatever") == "Ordinary"
