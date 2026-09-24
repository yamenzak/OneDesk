"""Intake, stage 1: every kind of file read into text without a site or a model.

Samples are built here rather than kept as files, so each test shows exactly
what it feeds the reader.
"""

import io
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from onedesk.one_intake import language, read, split
from onedesk.one_intake.readers import bank, card, einvoice, mail

UBL = """<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
 xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
 xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
 <cbc:ID>RE-2026-0042</cbc:ID>
 <cbc:IssueDate>2026-09-01</cbc:IssueDate>
 <cbc:DueDate>2026-09-15</cbc:DueDate>
 <cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>
 <cbc:DocumentCurrencyCode>EUR</cbc:DocumentCurrencyCode>
 <cbc:BuyerReference>04011000-12345-34</cbc:BuyerReference>
 <cac:InvoicePeriod><cbc:StartDate>2026-08-01</cbc:StartDate><cbc:EndDate>2026-08-31</cbc:EndDate></cac:InvoicePeriod>
 <cac:OrderReference><cbc:ID>PO-7</cbc:ID></cac:OrderReference>
 <cac:AccountingSupplierParty><cac:Party>
  <cbc:EndpointID schemeID="EM">rechnung@stadtwerke.example</cbc:EndpointID>
  <cac:PartyName><cbc:Name>Stadtwerke</cbc:Name></cac:PartyName>
  <cac:PostalAddress><cbc:StreetName>Parkgürtel 24</cbc:StreetName><cbc:CityName>Köln</cbc:CityName>
   <cbc:PostalZone>50823</cbc:PostalZone><cac:Country><cbc:IdentificationCode>DE</cbc:IdentificationCode></cac:Country></cac:PostalAddress>
  <cac:PartyTaxScheme><cbc:CompanyID>DE 123 456 789</cbc:CompanyID><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:PartyTaxScheme>
  <cac:PartyLegalEntity><cbc:RegistrationName>Stadtwerke Köln GmbH</cbc:RegistrationName></cac:PartyLegalEntity>
 </cac:Party></cac:AccountingSupplierParty>
 <cac:AccountingCustomerParty><cac:Party><cac:PartyName><cbc:Name>Acme GmbH</cbc:Name></cac:PartyName></cac:Party></cac:AccountingCustomerParty>
 <cac:PaymentMeans><cbc:PaymentMeansCode>58</cbc:PaymentMeansCode><cbc:PaymentID>KD 4711</cbc:PaymentID>
  <cac:PayeeFinancialAccount><cbc:ID>DE89 3704 0044 0532 0130 00</cbc:ID></cac:PayeeFinancialAccount></cac:PaymentMeans>
 <cac:TaxTotal><cbc:TaxAmount currencyID="EUR">13.44</cbc:TaxAmount></cac:TaxTotal>
 <cac:LegalMonetaryTotal>
  <cbc:LineExtensionAmount currencyID="EUR">70.76</cbc:LineExtensionAmount>
  <cbc:TaxExclusiveAmount currencyID="EUR">70.76</cbc:TaxExclusiveAmount>
  <cbc:TaxInclusiveAmount currencyID="EUR">84.20</cbc:TaxInclusiveAmount>
  <cbc:PayableAmount currencyID="EUR">84.20</cbc:PayableAmount>
 </cac:LegalMonetaryTotal>
 <cac:InvoiceLine><cbc:ID>1</cbc:ID><cbc:InvoicedQuantity unitCode="KWH">250</cbc:InvoicedQuantity>
  <cbc:LineExtensionAmount currencyID="EUR">70.76</cbc:LineExtensionAmount>
  <cac:Item><cbc:Name>Strom August</cbc:Name><cac:ClassifiedTaxCategory><cbc:Percent>19</cbc:Percent></cac:ClassifiedTaxCategory></cac:Item>
  <cac:Price><cbc:PriceAmount currencyID="EUR">0.28304</cbc:PriceAmount></cac:Price></cac:InvoiceLine>
</Invoice>""".encode()

CII = """<?xml version="1.0" encoding="UTF-8"?>
<rsm:CrossIndustryInvoice xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
 xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
 xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100">
 <rsm:ExchangedDocument><ram:ID>GS-9</ram:ID><ram:TypeCode>381</ram:TypeCode>
  <ram:IssueDateTime><udt:DateTimeString format="102">20260903</udt:DateTimeString></ram:IssueDateTime></rsm:ExchangedDocument>
 <rsm:SupplyChainTradeTransaction>
  <ram:IncludedSupplyChainTradeLineItem>
   <ram:SpecifiedTradeProduct><ram:SellerAssignedID>A-1</ram:SellerAssignedID><ram:Name>Druckerpapier</ram:Name></ram:SpecifiedTradeProduct>
   <ram:SpecifiedLineTradeAgreement><ram:NetPriceProductTradePrice><ram:ChargeAmount>5.00</ram:ChargeAmount></ram:NetPriceProductTradePrice></ram:SpecifiedLineTradeAgreement>
   <ram:SpecifiedLineTradeDelivery><ram:BilledQuantity unitCode="H87">2</ram:BilledQuantity></ram:SpecifiedLineTradeDelivery>
   <ram:SpecifiedLineTradeSettlement><ram:ApplicableTradeTax><ram:RateApplicablePercent>19</ram:RateApplicablePercent></ram:ApplicableTradeTax>
    <ram:SpecifiedTradeSettlementLineMonetarySummation><ram:LineTotalAmount>10.00</ram:LineTotalAmount></ram:SpecifiedTradeSettlementLineMonetarySummation></ram:SpecifiedLineTradeSettlement>
  </ram:IncludedSupplyChainTradeLineItem>
  <ram:ApplicableHeaderTradeAgreement>
   <ram:SellerTradeParty><ram:Name>Büro Meier</ram:Name>
    <ram:PostalTradeAddress><ram:PostcodeCode>10115</ram:PostcodeCode><ram:CityName>Berlin</ram:CityName><ram:CountryID>DE</ram:CountryID></ram:PostalTradeAddress>
    <ram:SpecifiedTaxRegistration><ram:ID schemeID="VA">DE999999999</ram:ID></ram:SpecifiedTaxRegistration>
    <ram:SpecifiedTaxRegistration><ram:ID schemeID="FC">27/123/45678</ram:ID></ram:SpecifiedTaxRegistration>
   </ram:SellerTradeParty>
   <ram:BuyerTradeParty><ram:Name>Acme GmbH</ram:Name></ram:BuyerTradeParty>
  </ram:ApplicableHeaderTradeAgreement>
  <ram:ApplicableHeaderTradeSettlement>
   <ram:PaymentReference>GS-9</ram:PaymentReference><ram:InvoiceCurrencyCode>EUR</ram:InvoiceCurrencyCode>
   <ram:SpecifiedTradeSettlementPaymentMeans><ram:TypeCode>59</ram:TypeCode></ram:SpecifiedTradeSettlementPaymentMeans>
   <ram:SpecifiedTradeSettlementHeaderMonetarySummation>
    <ram:LineTotalAmount>10.00</ram:LineTotalAmount><ram:TaxBasisTotalAmount>10.00</ram:TaxBasisTotalAmount>
    <ram:TaxTotalAmount currencyID="EUR">1.90</ram:TaxTotalAmount><ram:GrandTotalAmount>11.90</ram:GrandTotalAmount>
    <ram:DuePayableAmount>11.90</ram:DuePayableAmount>
   </ram:SpecifiedTradeSettlementHeaderMonetarySummation>
  </ram:ApplicableHeaderTradeSettlement>
 </rsm:SupplyChainTradeTransaction>
</rsm:CrossIndustryInvoice>""".encode()

CAMT = """<?xml version="1.0"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.08"><BkToCstmrStmt><Stmt>
 <Acct><Id><IBAN>DE02120300000000202051</IBAN></Id><Ccy>EUR</Ccy></Acct>
 <Bal><Tp><CdOrPrtry><Cd>OPBD</Cd></CdOrPrtry></Tp><Amt Ccy="EUR">1000.00</Amt><CdtDbtInd>CRDT</CdtDbtInd></Bal>
 <Bal><Tp><CdOrPrtry><Cd>CLBD</Cd></CdOrPrtry></Tp><Amt Ccy="EUR">915.80</Amt><CdtDbtInd>CRDT</CdtDbtInd></Bal>
 <Ntry><Amt Ccy="EUR">84.20</Amt><CdtDbtInd>DBIT</CdtDbtInd><BookgDt><Dt>2026-09-15</Dt></BookgDt>
  <NtryDtls><TxDtls><Refs><EndToEndId>KD4711</EndToEndId></Refs>
   <RltdPties><Cdtr><Nm>Stadtwerke Koeln GmbH</Nm></Cdtr><CdtrAcct><Id><IBAN>DE89370400440532013000</IBAN></Id></CdtrAcct></RltdPties>
   <RmtInf><Ustrd>RE-2026-0042 KD 4711</Ustrd></RmtInf></TxDtls></NtryDtls></Ntry>
</Stmt></BkToCstmrStmt></Document>""".encode()

MT = """:20:STARTUMSE
:25:DE02120300000000202051
:28C:00001/001
:60F:C260914EUR1000,00
:61:2609150915DR84,20NMSCNONREF
:86:177?00SEPA-UEBERWEISUNG?20RE-2026-0042 ?21KD 4711?32Stadtwerke Koeln?33 GmbH?38DE89370400440532013000
:62F:C260915EUR915,80
-"""


def test_ubl_invoice_is_read_field_by_field():
	said = einvoice.parse(UBL)
	assert said["format"] == "UBL" and said["kind"] == "invoice"
	assert (said["number"], said["issued"], said["due"], said["currency"]) == ("RE-2026-0042", "2026-09-01", "2026-09-15", "EUR")
	assert said["seller"]["name"] == "Stadtwerke Köln GmbH", "the registered name wins over the trading name"
	assert said["seller"]["vat_id"] == "DE123456789", "spaces are gone"
	assert said["seller"]["email"] == "rechnung@stadtwerke.example"
	assert said["payment"] == {"iban": "DE89370400440532013000", "reference": "KD 4711", "means": "transfer"}
	assert said["totals"]["payable"] == 84.20 and said["totals"]["tax"] == 13.44
	assert said["lines"][0] == {"name": "Strom August", "code": None, "qty": 250.0, "unit": "KWH", "price": 0.28304, "amount": 70.76, "tax_rate": 19.0}
	assert said["period"] == ["2026-08-01", "2026-08-31"] and said["order"] == "PO-7"
	assert "DE89370400440532013000" in einvoice.described(said)


def test_cii_credit_note_with_direct_debit():
	said = einvoice.parse(CII)
	assert said["format"] == "CII" and said["kind"] == "credit note"
	assert said["issued"] == "2026-09-03", "format 102 is read"
	assert said["seller"]["vat_id"] == "DE999999999" and said["seller"]["tax_id"] == "27/123/45678"
	assert said["payment"]["means"] == "direct debit"
	assert said["lines"][0]["qty"] == 2.0 and said["lines"][0]["amount"] == 10.0
	assert said["totals"]["gross"] == 11.90


def test_what_is_not_an_invoice_is_not_one():
	assert einvoice.parse(b"<html><body>hi</body></html>") is None
	assert einvoice.parse(b"not xml") is None
	assert einvoice.parse(b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "b">]><Invoice/>') is None, "no entities"


def test_camt_statement_lines_carry_who_and_what():
	said = bank.camt(CAMT)
	assert said["account_iban"] == "DE02120300000000202051"
	assert (said["opening"], said["closing"]) == (1000.0, 915.8)
	entry = said["entries"][0]
	assert entry["amount"] == -84.2, "a debit is negative"
	assert entry["party"] == "Stadtwerke Koeln GmbH" and entry["party_iban"] == "DE89370400440532013000"
	assert entry["text"] == "RE-2026-0042 KD 4711" and entry["date"] == "2026-09-15"


def test_mt940_statement_reads_the_same_facts():
	said = bank.mt940(MT)
	assert said["account_iban"] == "DE02120300000000202051"
	assert said["opening"] == 1000.0 and said["closing"] == 915.8
	entry = said["entries"][0]
	assert entry["amount"] == -84.2 and entry["date"] == "2026-09-15"
	assert entry["party"] == "Stadtwerke Koeln GmbH"
	assert entry["party_iban"] == "DE89370400440532013000"
	assert "RE-2026-0042" in entry["text"]
	assert bank.mt940("just a letter") is None


def test_the_dispatcher_knows_a_statement_by_its_content():
	assert read.read("export.txt", MT.encode()).how == "Bank statement"
	assert read.read("auszug.xml", CAMT).structured["statement"]["entries"]
	assert read.read("rechnung.xml", UBL).how == "E-invoice"


FORWARD = """Hi Anna, can you pay this?

---------- Forwarded message ---------
From: Stadtwerke Köln <rechnung@stadtwerke.example>
Date: Mon, 1 Sep 2026 at 09:12
Subject: Ihre Rechnung RE-2026-0042
To: <ahmad@acme.example>

Sehr geehrte Damen und Herren, anbei Ihre Rechnung.
"""


def test_a_forward_is_unwrapped_to_the_original():
	said = mail.unwrap(FORWARD)
	assert said["from_email"] == "rechnung@stadtwerke.example"
	assert said["from_name"] == "Stadtwerke Köln"
	assert said["subject"] == "Ihre Rechnung RE-2026-0042"
	assert said["note"] == "Hi Anna, can you pay this?"
	assert said["text"].startswith("Sehr geehrte")


def test_nested_forwards_reach_the_innermost_and_outlook_has_no_marker():
	outlook = (
		"FYI\n\nVon: Buchhaltung <buha@acme.example>\nGesendet: Montag, 1. September 2026\nAn: Ahmad\nBetreff: WG: Rechnung\n\n"
		"-----Ursprüngliche Nachricht-----\nVon: Lieferant [mailto:info@lieferant.example]\nBetreff: Rechnung 9\n\nBitte zahlen."
	)
	said = mail.unwrap(outlook)
	assert said["from_email"] == "info@lieferant.example" and said["subject"] == "Rechnung 9"
	assert said["note"] == "FYI"
	assert mail.unwrap("Just a normal message\nwith no forward.") is None


def test_an_eml_gives_its_headers_words_and_attachments():
	raw = (
		b"From: Stadtwerke <rechnung@stadtwerke.example>\r\nTo: ahmad@acme.example\r\nSubject: Rechnung\r\n"
		b"Message-ID: <abc@stadtwerke.example>\r\nMIME-Version: 1.0\r\n"
		b'Content-Type: multipart/mixed; boundary="b"\r\n\r\n--b\r\nContent-Type: text/html; charset=utf-8\r\n\r\n'
		b"<p>Anbei&nbsp;die <b>Rechnung</b></p><style>p{}</style>\r\n--b\r\n"
		b'Content-Type: application/pdf\r\nContent-Disposition: attachment; filename="re.pdf"\r\n'
		b"Content-Transfer-Encoding: base64\r\n\r\nJVBERi0=\r\n--b--\r\n"
	)
	said = read.read("mail.eml", raw)
	assert said.how == "Mail" and said.structured["mail"]["message_id"] == "abc@stadtwerke.example"
	assert said.text == "Rechnung\n\nAnbei die Rechnung"
	assert said.inner == [{"name": "re.pdf", "content": b"%PDF-"}]


def test_cards_and_invitations():
	vcf = "BEGIN:VCARD\r\nVERSION:3.0\r\nN:Weber;Anna;;;\r\nORG:Kanzlei Weber\r\nTITLE:Steuerberaterin\r\nEMAIL;TYPE=work:Anna@Weber.example\r\nTEL:+49 221 123\r\nADR;TYPE=work:;;Ring 1;Köln;;50667;DE\r\nEND:VCARD\r\n"
	said = card.vcards(vcf)[0]
	assert said["name"] == "Anna Weber" and said["organisation"] == "Kanzlei Weber"
	assert said["emails"] == ["anna@weber.example"] and said["addresses"][0]["city"] == "Köln"
	ics = "BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nSUMMARY:Termin Finanzamt\r\nDTSTART;TZID=Europe/Berlin:20261012T093000\r\nDTEND:20261012T100000\r\nLOCATION:Zimmer 2\\, EG\r\nORGANIZER:mailto:amt@finanzamt.example\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n"
	event = card.events(ics)[0]
	assert event["summary"] == "Termin Finanzamt" and event["starts"] == "2026-10-12 09:30:00"
	assert event["time_zone"] == "Europe/Berlin" and event["location"] == "Zimmer 2, EG"
	assert read.read("invite.ics", ics.encode()).how == "Invitation"


def _zip(files: dict) -> bytes:
	buffer = io.BytesIO()
	with zipfile.ZipFile(buffer, "w") as held:
		for name, text in files.items():
			held.writestr(name, text)
	return buffer.getvalue()


def test_word_and_slides_are_read_without_running_anything():
	docx = _zip(
		{
			"[Content_Types].xml": "<Types/>",
			"word/document.xml": '<w:document xmlns:w="w"><w:body><w:p><w:r><w:t>Kündigung</w:t></w:r></w:p>'
			"<w:p><w:r><w:t>zum 30.11.</w:t><w:tab/><w:t>2026</w:t></w:r></w:p></w:body></w:document>",
			"word/vbaProject.bin": "macro",
		}
	)
	said = read.read("brief.docx", docx)
	assert said.how == "Word" and said.text == "Kündigung\nzum 30.11.\t2026"
	pptx = _zip({"ppt/slides/slide2.xml": '<p:sld xmlns:p="p" xmlns:a="a"><a:p><a:t>Zwei</a:t></a:p></p:sld>', "ppt/slides/slide1.xml": '<p:sld xmlns:p="p" xmlns:a="a"><a:p><a:t>Eins</a:t></a:p></p:sld>'})
	assert read.read("deck.pptx", pptx).text == "[Slide 1]\nEins\n\n[Slide 2]\nZwei"


def test_a_zip_is_its_files_and_a_bomb_is_refused():
	said = read.read("belege.zip", _zip({"a/1.txt": "eins", "__MACOSX/x": "junk", "2.xml": "<x>zwei</x>"}))
	assert said.how == "Archive" and [one["name"] for one in said.inner] == ["1.txt", "2.xml"]
	many = _zip({f"{index}.txt": "x" for index in range(read.MOST_MEMBERS + 1)})
	assert read.read("many.zip", many).needs == "nothing"


def test_sheets_and_csv():
	import openpyxl

	book = openpyxl.Workbook()
	book.active.title = "Belege"
	book.active.append(["Datum", "Betrag"])
	book.active.append(["2026-09-01", 84.2])
	buffer = io.BytesIO()
	book.save(buffer)
	assert read.read("belege.xlsx", buffer.getvalue()).text == "[Belege]\nDatum\tBetrag\n2026-09-01\t84.2"
	csv = "Datum;Betrag\n01.09.2026;84,20\n".encode("cp1252")
	assert read.read("export.csv", csv).text == "Datum\tBetrag\n01.09.2026\t84,20"


def test_what_needs_a_model_says_so():
	assert read.read("scan.jpg", b"\xff\xd8").needs == "eyes"
	assert read.read("voicemail.m4a", b"....").needs == "ears"
	assert read.read("mail.msg", b"\xd0\xcf").needs == "nothing"
	assert read.read("thing.bin", b"\x00\x01").needs == "nothing"


def test_a_batch_scan_is_cut_at_blanks_separators_and_numbering():
	pages = [
		"Stadtwerke Köln\nRechnung\nSeite 1 von 2",
		"Summe 84,20\nSeite 2 von 2",
		"Finanzamt Köln\nBescheid über Einkommensteuer",
		"",
		"Allianz\nIhre Police",
		"TRENNBLATT",
		"Kanzlei Weber\nSeite 1 von 1",
	]
	assert split.documents(pages) == [[0, 1], [2], [4], [6]]


def test_duplex_backs_are_dropped_not_cut_and_a_model_may_mark_starts():
	pages = ["Brief A Seite eins", "", "Brief A weiter", "", "Brief B", "", "Brief B weiter", ""]
	assert split.documents(pages) == [[0, 2, 4, 6]], "blank backs of a two-sided scan are not gaps"
	assert split.documents(pages, starts={4}) == [[0, 2], [4, 6]]
	assert split.documents(["Brief A", "Brief A weiter", "Brief B", "", "Brief C"]) == [[0, 1, 2], [4]], "one blank is a gap"
	assert split.numbered("... Page 3 of 7") == (3, 7)
	assert split.numbered("Datum 1/3/2026") is None, "a date is not a page number"


def test_language_by_its_small_words():
	assert language.guess("Sehr geehrte Damen und Herren, die Rechnung ist nicht bezahlt.") == "de"
	assert language.guess("Please find the invoice attached, we are not able to pay.") == "en"
	assert language.guess("مرحبا، هذه هي الفاتورة الخاصة بكم") == "ar"
	assert language.guess("12345 67890") is None


def test_a_text_layer_is_told_from_a_scans_leftovers():
	from onedesk.one_intake.readers import pdf

	letter = "Sehr geehrte Damen und Herren, anbei die Rechnung."
	assert pdf.has_text([letter, "", letter, " ", "Summe 84,20 Seite 2 von 2 insgesamt"]), "blank separators do not count"
	assert not pdf.has_text(["", "1", "", "2"]), "page numbers are not a text layer"
	assert not pdf.has_text(["x7", letter[:10], "3"])
	assert not pdf.has_text([])


def test_what_the_index_is_asked_for():
	import ast
	import re

	space = {"re": re}
	source = (Path(__file__).resolve().parent.parent / "onedesk" / "one_intake" / "search.py").read_text()
	for node in ast.parse(source).body:
		if (isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "SKIP") or (
			isinstance(node, ast.FunctionDef) and node.name == "words"
		):
			exec(ast.unparse(node), space)
	words = space["words"]
	assert words('Rechnung "RE-2026" +Stadtwerke -x (Köln)') == ["rechnung", "2026", "stadtwerke", "köln"], "operators gone"
	assert words("the invoice and the tax") == ["invoice", "tax"], "stopwords the index skips anyway"
	assert words("a b") == []
