"""E-invoices read as data: XRechnung and Peppol (UBL), ZUGFeRD and Factur-X (CII).

An e-invoice already says, field by field, who sent it, what it costs and
where to pay. Reading it with a model would be paying to guess at what is
written down. Pure.
"""

from decimal import Decimal, InvalidOperation

from onedesk.one_intake.readers import markup as m

#: UNTDID 1001: what a document says it is.
CREDIT_NOTES = {"381", "396", "532"}

#: UNTDID 4461: how it is paid.
DEBITED = {"49", "59"}
TRANSFERRED = {"30", "31", "42", "58"}


def parse(content: bytes) -> dict | None:
	"""The invoice as a dict, or None when this is not an e-invoice."""
	root = m.root(content)
	if root is None:
		return None
	name = m.local(root.tag)
	if name in ("Invoice", "CreditNote"):
		return _ubl(root, name)
	if name == "CrossIndustryInvoice":
		return _cii(root)
	return None


def described(invoice: dict) -> str:
	"""The invoice as lines a person, a search index or a model can read."""
	seller, buyer, pay, totals = (invoice.get(key) or {} for key in ("seller", "buyer", "payment", "totals"))
	said = [
		f"{invoice['kind'].title()} {invoice.get('number') or ''}".strip(),
		f"From: {_party(seller)}",
		f"To: {_party(buyer)}",
		f"Issued: {invoice.get('issued') or ''}",
	]
	if invoice.get("due"):
		said.append(f"Due: {invoice['due']}")
	if invoice.get("period"):
		said.append(f"Period: {invoice['period'][0] or ''} to {invoice['period'][1] or ''}")
	if invoice.get("order"):
		said.append(f"Order: {invoice['order']}")
	for line in invoice.get("lines") or []:
		said.append(
			f"- {line.get('name') or ''}: {line.get('qty') or ''} {line.get('unit') or ''} "
			f"× {line.get('price') or ''} = {line.get('amount') or ''}"
		)
	currency = invoice.get("currency") or ""
	said.append(
		f"Net {totals.get('net')} {currency}, tax {totals.get('tax')}, gross {totals.get('gross')}, "
		f"payable {totals.get('payable')}"
	)
	if pay.get("iban"):
		said.append(f"Pay to IBAN {pay['iban']}, reference {pay.get('reference') or ''}")
	if pay.get("means"):
		said.append(f"Paid by {pay['means']}")
	return "\n".join(said)


def _party(party: dict) -> str:
	bits = [party.get("name"), party.get("vat_id") and f"VAT {party['vat_id']}", party.get("city")]
	return ", ".join(bit for bit in bits if bit)


# ------------------------------------------------------------------ UBL


def _ubl(root, name: str) -> dict:
	type_code = m.text(root, "InvoiceTypeCode") or m.text(root, "CreditNoteTypeCode") or ""
	means = m.find(root, "PaymentMeans")
	line_tag, quantity_tag = ("CreditNoteLine", "CreditedQuantity") if name == "CreditNote" else ("InvoiceLine", "InvoicedQuantity")
	totals = m.find(root, "LegalMonetaryTotal")
	return {
		"format": "UBL",
		"kind": "credit note" if name == "CreditNote" or type_code in CREDIT_NOTES else "invoice",
		"number": m.text(root, "ID"),
		"issued": _date(m.text(root, "IssueDate")),
		"due": _date(m.text(root, "DueDate") or m.text(means, "PaymentDueDate")),
		"currency": m.text(root, "DocumentCurrencyCode"),
		"order": m.text(root, "OrderReference/ID"),
		"buyer_reference": m.text(root, "BuyerReference"),
		"period": _period(m.text(root, "InvoicePeriod/StartDate"), m.text(root, "InvoicePeriod/EndDate")),
		"seller": _ubl_party(m.find(root, "AccountingSupplierParty/Party")),
		"buyer": _ubl_party(m.find(root, "AccountingCustomerParty/Party")),
		"payment": {
			"iban": _iban(m.text(means, "PayeeFinancialAccount/ID")),
			"reference": m.text(means, "PaymentID"),
			"means": _means(m.text(means, "PaymentMeansCode")),
		},
		"lines": [
			{
				"name": m.text(line, "Item/Name"),
				"code": m.text(line, "Item/SellersItemIdentification/ID"),
				"qty": _number(m.text(line, quantity_tag)),
				"unit": m.attribute(line, quantity_tag, "unitCode"),
				"price": _number(m.text(line, "Price/PriceAmount")),
				"amount": _number(m.text(line, "LineExtensionAmount")),
				"tax_rate": _number(m.text(line, "Item/ClassifiedTaxCategory/Percent")),
			}
			for line in m.children(root, line_tag)
		],
		"totals": {
			"net": _number(m.text(totals, "TaxExclusiveAmount") or m.text(totals, "LineExtensionAmount")),
			"tax": _number(m.text(root, "TaxTotal/TaxAmount")),
			"gross": _number(m.text(totals, "TaxInclusiveAmount")),
			"prepaid": _number(m.text(totals, "PrepaidAmount")),
			"payable": _number(m.text(totals, "PayableAmount")),
		},
	}


def _ubl_party(party) -> dict:
	if party is None:
		return {}
	vat = tax = None
	for scheme in m.children(party, "PartyTaxScheme"):
		company = m.text(scheme, "CompanyID")
		if (m.text(scheme, "TaxScheme/ID") or "").upper() == "VAT":
			vat = company
		else:
			tax = company
	endpoint = m.text(party, "EndpointID")
	return _clean(
		{
			"name": m.text(party, "PartyLegalEntity/RegistrationName") or m.text(party, "PartyName/Name"),
			"vat_id": _compact(vat),
			"tax_id": tax,
			"register": m.text(party, "PartyLegalEntity/CompanyID"),
			"street": m.text(party, "PostalAddress/StreetName"),
			"city": m.text(party, "PostalAddress/CityName"),
			"postcode": m.text(party, "PostalAddress/PostalZone"),
			"country": m.text(party, "PostalAddress/Country/IdentificationCode"),
			"contact": m.text(party, "Contact/Name"),
			"phone": m.text(party, "Contact/Telephone"),
			"email": m.text(party, "Contact/ElectronicMail") or (endpoint if endpoint and "@" in endpoint else None),
		}
	)


# ------------------------------------------------------------------ CII


def _cii(root) -> dict:
	document = m.find(root, "ExchangedDocument")
	trade = m.find(root, "SupplyChainTradeTransaction")
	agreement = m.find(trade, "ApplicableHeaderTradeAgreement")
	settlement = m.find(trade, "ApplicableHeaderTradeSettlement")
	means = m.find(settlement, "SpecifiedTradeSettlementPaymentMeans")
	sums = m.find(settlement, "SpecifiedTradeSettlementHeaderMonetarySummation")
	return {
		"format": "CII",
		"kind": "credit note" if (m.text(document, "TypeCode") or "") in CREDIT_NOTES else "invoice",
		"number": m.text(document, "ID"),
		"issued": _date(m.text(document, "IssueDateTime/DateTimeString")),
		"due": _date(m.text(settlement, "SpecifiedTradePaymentTerms/DueDateDateTime/DateTimeString")),
		"currency": m.text(settlement, "InvoiceCurrencyCode"),
		"order": m.text(agreement, "BuyerOrderReferencedDocument/IssuerAssignedID"),
		"buyer_reference": m.text(agreement, "BuyerReference"),
		"period": _period(
			m.text(settlement, "BillingSpecifiedPeriod/StartDateTime/DateTimeString"),
			m.text(settlement, "BillingSpecifiedPeriod/EndDateTime/DateTimeString"),
		),
		"seller": _cii_party(m.find(agreement, "SellerTradeParty")),
		"buyer": _cii_party(m.find(agreement, "BuyerTradeParty")),
		"payment": {
			"iban": _iban(m.text(means, "PayeePartyCreditorFinancialAccount/IBANID")),
			"reference": m.text(settlement, "PaymentReference"),
			"means": _means(m.text(means, "TypeCode")),
		},
		"lines": [
			{
				"name": m.text(line, "SpecifiedTradeProduct/Name"),
				"code": m.text(line, "SpecifiedTradeProduct/SellerAssignedID"),
				"qty": _number(m.text(line, "SpecifiedLineTradeDelivery/BilledQuantity")),
				"unit": m.attribute(line, "SpecifiedLineTradeDelivery/BilledQuantity", "unitCode"),
				"price": _number(
					m.text(line, "SpecifiedLineTradeAgreement/NetPriceProductTradePrice/ChargeAmount")
				),
				"amount": _number(
					m.text(line, "SpecifiedLineTradeSettlement/SpecifiedTradeSettlementLineMonetarySummation/LineTotalAmount")
				),
				"tax_rate": _number(
					m.text(line, "SpecifiedLineTradeSettlement/ApplicableTradeTax/RateApplicablePercent")
				),
			}
			for line in m.children(trade, "IncludedSupplyChainTradeLineItem")
		],
		"totals": {
			"net": _number(m.text(sums, "TaxBasisTotalAmount") or m.text(sums, "LineTotalAmount")),
			"tax": _number(m.text(sums, "TaxTotalAmount")),
			"gross": _number(m.text(sums, "GrandTotalAmount")),
			"prepaid": _number(m.text(sums, "TotalPrepaidAmount")),
			"payable": _number(m.text(sums, "DuePayableAmount")),
		},
	}


def _cii_party(party) -> dict:
	if party is None:
		return {}
	vat = tax = None
	for registration in m.children(party, "SpecifiedTaxRegistration"):
		scheme = (m.attribute(registration, "ID", "schemeID") or "").upper()
		if scheme == "VA":
			vat = m.text(registration, "ID")
		elif scheme == "FC":
			tax = m.text(registration, "ID")
	return _clean(
		{
			"name": m.text(party, "Name"),
			"vat_id": _compact(vat),
			"tax_id": tax,
			"register": m.text(party, "SpecifiedLegalOrganization/ID"),
			"street": m.text(party, "PostalTradeAddress/LineOne"),
			"city": m.text(party, "PostalTradeAddress/CityName"),
			"postcode": m.text(party, "PostalTradeAddress/PostcodeCode"),
			"country": m.text(party, "PostalTradeAddress/CountryID"),
			"contact": m.text(party, "DefinedTradeContact/PersonName"),
			"phone": m.text(party, "DefinedTradeContact/TelephoneUniversalCommunication/CompleteNumber"),
			"email": m.text(party, "DefinedTradeContact/EmailURIUniversalCommunication/URIID")
			or m.text(party, "URIUniversalCommunication/URIID"),
		}
	)


# ------------------------------------------------------------------ values


def _date(value: str | None) -> str | None:
	"""ISO from either ISO or CII's format 102 (YYYYMMDD)."""
	value = (value or "").strip()
	if len(value) == 8 and value.isdigit():
		return f"{value[:4]}-{value[4:6]}-{value[6:]}"
	return value[:10] if len(value) >= 10 and value[4] == "-" else None


def _period(start: str | None, end: str | None) -> list | None:
	start, end = _date(start), _date(end)
	return [start, end] if start or end else None


def _number(value: str | None) -> float | None:
	try:
		return float(Decimal((value or "").strip()))
	except (InvalidOperation, ValueError):
		return None


def _compact(value: str | None) -> str | None:
	return "".join(value.split()).upper() if value else None


def _iban(value: str | None) -> str | None:
	return _compact(value)


def _means(code: str | None) -> str | None:
	if code in DEBITED:
		return "direct debit"
	if code in TRANSFERRED:
		return "transfer"
	return None


def _clean(party: dict) -> dict:
	return {key: value for key, value in party.items() if value}
