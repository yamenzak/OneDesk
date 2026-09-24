"""Intake, stage 2: an identifier is recognised however it was typed, and a
wrong one is not an identifier at all."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from onedesk.one_intake import identifiers as ids

HOOKS = (Path(__file__).resolve().parent.parent / "onedesk" / "hooks.py").read_text()


def test_an_iban_is_checked_not_only_tidied():
	assert ids.iban("DE89 3704 0044 0532 0130 00") == "DE89370400440532013000"
	assert ids.iban("de89-3704-0044-0532-0130-00") == "DE89370400440532013000"
	assert ids.iban("DE88 3704 0044 0532 0130 00") is None, "one digit off is somebody else's account"
	assert ids.iban("DE89 3704 0044 0532 0130") is None, "a German IBAN is 22 characters"
	assert ids.iban("AE07 0331 2345 6789 0123 456") == "AE070331234567890123456"
	assert ids.iban("not an iban") is None and ids.iban(None) is None


def test_a_vat_id_and_a_tax_number_are_told_apart():
	assert ids.vat("DE 123 456 789") == "DE123456789"
	assert ids.vat("el094014298") == "EL094014298", "Greece writes EL"
	assert ids.tax_kind("DE123456789") == ids.VAT
	assert ids.tax_kind("27/123/45678") == ids.TAX and ids.tax_number("27/123/45678") == "2712345678"
	assert ids.tax_kind("100234567800003") == ids.TAX, "a UAE TRN is fifteen digits"
	assert ids.tax_kind("hello") is None


def test_phones_have_their_country():
	assert ids.phone("+49 221 123456") == "+49221123456"
	assert ids.phone("0221 123456", "DE") == "+49221123456"
	assert ids.phone("0049 221 123456") == "+49221123456"
	assert ids.phone("050 123 4567", "AE") == "+971501234567"
	assert ids.phone("call me") is None


def test_emails_domains_and_websites():
	assert ids.email(" <Anna@Weber.Example> ") == "anna@weber.example"
	assert ids.email("mailto:info@acme.example") == "info@acme.example"
	assert ids.email("not@valid") is None
	assert ids.domain("https://www.Stadtwerke-Koeln.de/kontakt") == "stadtwerke-koeln.de"
	assert ids.organisation_domain("someone@gmail.com") is None, "a mail provider is not the organisation"
	assert ids.organisation_domain("rechnung@stadtwerke.example") == "stadtwerke.example"


def test_register_and_document_numbers():
	assert ids.register("HRB 12345") == "HRB12345"
	assert ids.register("12345") is None
	assert ids.document("C01X00T47") == "C01X00T47"
	assert ids.document("L01X-00T4 7") == "L01X00T47"
	assert ids.document("ABCDE") is None, "a number has digits"


def test_found_reads_a_records_values_into_canonical_pairs():
	said = ids.found(
		[
			("Tax ID", "DE 123 456 789"),
			(ids.WEBSITE, "https://www.stadtwerke.example"),
			(ids.EMAIL, "Rechnung@Stadtwerke.example"),
			(ids.IBAN, "DE89 3704 0044 0532 0130 00"),
			(ids.PHONE, "0221 123456"),
			(ids.IBAN, "wrong"),
			(ids.EMAIL, "someone@gmail.com"),
		]
	)
	assert said == [
		(ids.VAT, "DE123456789"),
		(ids.DOMAIN, "stadtwerke.example"),
		(ids.EMAIL, "rechnung@stadtwerke.example"),
		(ids.IBAN, "DE89370400440532013000"),
		(ids.PHONE, "+49221123456"),
		(ids.EMAIL, "someone@gmail.com"),
	], "a website and an email name the same domain once; gmail names no organisation"


def test_the_registry_follows_every_save_rename_and_delete():
	assert '"on_update": "onedesk.one_intake.identity.remember"' in HOOKS
	assert '"after_rename": "onedesk.one_intake.identity.renamed"' in HOOKS
	assert "onedesk.one_intake.identity.forget" in HOOKS
	assert "onedesk.one_intake.identity.flag" in HOOKS
	source = (Path(__file__).resolve().parent.parent / "onedesk" / "one_intake" / "identity.py").read_text()
	assert "rename_doc(doctype, name, into, merge=True)" in source, "a merge is Frappe's own"
	assert "unique" not in (Path(__file__).resolve().parent.parent / "onedesk" / "one_intake" / "doctype" / "identifier" / "identifier.json").read_text(), (
		"a unique index would trip half way through a merge"
	)
