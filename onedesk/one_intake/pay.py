"""Pay from the document (docs/INTAKE.md §16.5).

A bill that asks to be paid by transfer shows, in the Intake panel, whom to
pay, the IBAN, the amount and the reference, each ready to copy, and a
GiroCode: the EPC QR code every European banking app scans into a filled-in
transfer. Nothing is paid from here; the bank does that, as the person.

**A changed IBAN stops it.** When the payee is a supplier we already hold
bank accounts for and the document's IBAN is none of them, there is no code,
and the panel says so in red: that is how invoice fraud works, and the one
safe answer is to ask the supplier on a number already known.
"""

import frappe
from frappe import _

from onedesk.one_intake import identifiers as ids

#: What the EPC code may carry (EPC069-12): euro only, up to this amount.
MOST = 999_999_999.99

#: Nothing to pay: paid already, or the bank collects it.
NOT_BY_TRANSFER = ("Direct Debit", "Already Paid")


def epc(name: str, iban: str, amount: float | None, reference: str | None = None, bic: str | None = None) -> str | None:
	"""The GiroCode's text (EPC069-12, version 002), or None when the
	payment cannot be one. Pure.

	A reference that is an ISO 11649 creditor reference (RF…) goes in the
	structured field, anything else in the free text; never both."""
	iban = (iban or "").replace(" ", "").upper()
	name = " ".join((name or "").split())[:70]
	if not iban or not name or (amount is not None and not 0.01 <= float(amount) <= MOST):
		return None
	reference = " ".join((reference or "").split())
	structured = reference.replace(" ", "").upper() if reference.upper().startswith("RF") else ""
	lines = [
		"BCD",
		"002",
		"1",
		"SCT",
		(bic or "").replace(" ", "").upper(),
		name,
		iban,
		f"EUR{float(amount):.2f}" if amount is not None else "",
		"",
		structured[:35],
		"" if structured else reference[:140],
	]
	return "\n".join(lines).rstrip("\n")


def of(doc) -> dict | None:
	"""What the panel shows to pay a Reading, or None when it asks nobody to
	pay by transfer."""
	if not doc.iban or doc.verdict == "Phishing" or doc.paid_how in NOT_BY_TRANSFER or doc.kind not in ("Invoice", "Reminder", "Tax Assessment", "Letter From an Authority", "Other", "Letter"):
		return None
	payee = next((row for row in doc.parties if row.role == "Paid To"), None) or next((row for row in doc.parties if row.role == "Sender"), None)
	name = (payee.party_name if payee else None) or ""
	iban = ids.iban(doc.iban) or doc.iban
	out = {"name": name, "iban": iban, "amount": doc.gross, "currency": doc.currency, "reference": doc.payment_reference or doc.number, "warn": None, "code": None}
	supplier = payee.matched_name if payee and payee.matched_doctype == "Supplier" else None
	if supplier:
		known = [one.replace(" ", "").upper() for one in frappe.get_all("Bank Account", filters={"party_type": "Supplier", "party": supplier}, pluck="iban") if one]
		if known and iban.replace(" ", "").upper() not in known:
			out["warn"] = _("This IBAN is not one we have for {0}. Ask them on a number you already know before paying anything.").format(supplier)
			return out
	if (doc.currency or "EUR") == "EUR":
		text = epc(name, iban, doc.gross, out["reference"])
		out["code"] = _svg(text) if text else None
	return out


def _svg(text: str) -> str:
	"""The code as an inline SVG, drawn by the library frappe already uses
	for its two-factor codes."""
	import io

	import pyqrcode

	buffer = io.BytesIO()
	pyqrcode.create(text, error="M", encoding="utf-8").svg(buffer, scale=3, quiet_zone=2, xmldecl=False, svgns=True, omithw=True)
	return buffer.getvalue().decode()
