"""What OneBook's accountant makes of what OneAI read (docs/ARC-AI.md, The
agents): a bill, a credit note or a paid receipt as a draft Purchase Invoice,
a payment advice as a draft Payment Entry, a statement's lines as Bank
Transactions, and a task to ask for an invoice nobody has. Pure: each
answers actions, which the agents' door takes."""

from datetime import timedelta

from frappe.utils import getdate

from onedesk.one_ai.reading.money import REAL, Action, _real


UNIT = "Nos"


def posting_day(today_: str, locked: str | None) -> tuple[str, bool]:
	"""The day a draft is dated: today, or the first open day after books
	locked up to a later date, and whether it moved. Pure."""
	if locked and getdate(today_) <= getdate(locked):
		return str(getdate(locked) + timedelta(days=1)), True
	return today_, False


def lines(reading: dict, items: dict, account: str | None = None) -> list[dict]:
	"""The reading's lines as invoice rows: an item where one was found, else
	the line's own words, booked to `account` (where this supplier's bills
	went last time). A reading with no lines is one row for its net. Pure."""
	out = []
	for index, one in enumerate(reading.get("lines") or []):
		qty = float(one.get("qty") or 1) or 1
		amount = one.get("amount")
		rate = one.get("unit_price") if one.get("unit_price") is not None else (float(amount) / qty if amount is not None else None)
		if rate is None:
			continue
		row = {"qty": qty, "rate": float(rate), "description": (one.get("text") or "")[:140]}
		if amount is not None and abs(round(float(rate), 2) * qty - float(amount)) > 0.005:
			row = {"qty": 1, "rate": float(amount), "description": f"{qty:g} × {rate:g} {(one.get('text') or '')}".strip()[:140]}
		item = items.get(index)
		if item:
			row["item_code"] = item
		else:
			row.update({"item_name": (one.get("text") or reading.get("title") or "?")[:140], "uom": UNIT})
			if account:
				row["expense_account"] = account
		out.append(row)
	if not out:
		amount = reading.get("net") if reading.get("net") is not None else reading.get("gross")
		if amount is not None:
			row = {"item_name": (reading.get("title") or "?")[:140], "description": (reading.get("summary") or "")[:140], "qty": 1, "rate": float(amount), "uom": UNIT}
			if account:
				row["expense_account"] = account
			out.append(row)
	return out


TAX_ROUNDING = 0.05


def taxed_by(reading: dict, templates: dict[float, str] | None) -> str | None:
	"""Which of the company's tax templates, by rate, charges what the
	document charges on its net: 19% on 70.76 is 13.44. None when it charges
	no tax or none match. Pure."""
	net, tax = reading.get("net"), reading.get("tax")
	if not net or not tax:
		return None
	return next(
		(name for rate, name in (templates or {}).items() if abs(float(net) * rate / 100 - float(tax)) <= TAX_ROUNDING),
		None,
	)


def purchase(reading: dict, ctx: dict) -> list[Action]:
	"""An invoice, a receipt the company paid, a credit note or a timesheet of
	hours worked, from a known supplier, as a draft."""
	kind = reading.get("kind")
	if not _real(reading, ctx) or kind not in ("Invoice", "Receipt", "Credit Note", "Timesheet") or not ctx.get("supplier") or ctx.get("sender_is_colleague"):
		return []
	if ctx.get("existing_invoice"):
		return [Action("Link", "Purchase Invoice", ctx["existing_invoice"], {"file": ctx.get("file")}, key="books|existing", sure=True)] if ctx.get("file") else []
	day, moved = posting_day(ctx["today"], ctx.get("locked"))
	remarks = [ctx["said"]["moved"].format(ctx["locked"])] if moved else []
	if reading.get("paid_how") == "Direct Debit":
		remarks.append(ctx["said"]["direct_debit"])
	elif reading.get("paid_how") == "Already Paid" or kind == "Receipt":
		remarks.append(ctx["said"]["paid"])
	if kind == "Timesheet":
		remarks.append(ctx["said"]["timesheet"])
	due = next((str(one["date"]) for one in reading.get("dates") or [] if one.get("what") == "Due" and one.get("date")), None)
	head = {
		"supplier": ctx["supplier"],
		"bill_no": reading.get("number"),
		"bill_date": reading.get("issued_on"),
		"posting_date": day,
		"set_posting_time": 1,
		"due_date": due if due and due >= day else None,
		"currency": reading.get("currency"),
		"company": ctx.get("company"),
		"remarks": " ".join(remarks) or None,
		"project": ctx.get("project"),
		"taxes_and_charges": taxed_by(reading, ctx.get("purchase_taxes")),
	}
	head = {key: value for key, value in head.items() if value}
	if kind == "Credit Note":
		if ctx.get("original_invoice"):
			return [Action("Create", "Purchase Invoice", values={"against": ctx["original_invoice"], **head}, key="books|credit", flow="onedesk.one_ai.reading.planning.debit_note")]
		return [Action("Create", "Purchase Invoice", values={**head, "is_return": 1, "items": [{**row, "qty": -abs(row["qty"])} for row in lines(reading, ctx.get("items") or {}, ctx.get("expense_account"))]}, key="books|credit", propose=True, why=ctx["said"]["no_original"])]
	if ctx.get("purchase_order") and kind != "Timesheet":
		return [Action("Create", "Purchase Invoice", values={"order": ctx["purchase_order"], **head}, key="books|invoice", flow="onedesk.one_ai.reading.planning.invoice_from_order", propose_on_error=True)]
	rows = lines(reading, ctx.get("items") or {}, ctx.get("expense_account"))
	if not rows:
		return []
	if head.get("project"):
		rows = [{**row, "project": head["project"]} for row in rows]
	return [Action("Create", "Purchase Invoice", values={**head, "items": rows}, key="books|invoice", propose_on_error=True)]


def payment(reading: dict, ctx: dict) -> list[Action]:
	"""A customer's payment advice, as a draft Payment Entry against our
	invoice it names."""
	if not _real(reading, ctx) or reading.get("kind") != "Payment Advice" or not ctx.get("sales_invoice"):
		return []
	values = {"invoice": ctx["sales_invoice"], "amount": reading.get("gross"), "reference_no": reading.get("payment_reference") or reading.get("number"), "reference_date": reading.get("issued_on") or ctx["today"]}
	return [Action("Create", "Payment Entry", values={k: v for k, v in values.items() if v}, key="books|payment", flow="onedesk.one_ai.reading.planning.payment_for", propose_on_error=True)]


def bank(reading: dict, ctx: dict) -> list[Action]:
	"""A bank statement's lines, as Bank Transactions on our account. A bank
	line is not a posting: ERPNext's reconciliation matches it later."""
	if not _real(reading, ctx) or reading.get("kind") != "Bank Statement" or not ctx.get("bank_account"):
		return []
	out = []
	for one in ctx.get("statement_lines") or []:
		amount = float(one.get("amount") or 0)
		values = {
			"bank_account": ctx["bank_account"],
			"date": one.get("date"),
			"deposit": amount if amount > 0 else 0,
			"withdrawal": -amount if amount < 0 else 0,
			"description": (one.get("text") or "")[:500],
			"reference_number": one.get("reference"),
			"transaction_id": one.get("id"),
			"bank_party_name": one.get("party"),
			"bank_party_iban": one.get("iban"),
			"currency": ctx.get("statement_currency"),
		}
		out.append(Action("Create", "Bank Transaction", values={k: v for k, v in values.items() if v not in (None, "")}, key=f"books|bank|{one.get('key')}", flow="onedesk.one_ai.reading.planning.bank_line", sure=True))
	return out


def never_received(reading: dict, ctx: dict) -> list[Action]:
	"""A reminder for an invoice nobody has: a task to ask for it, and a
	warning, since this is also how fraud begins."""
	if not ctx.get("books") or reading.get("verdict") not in REAL or ctx.get("history") or reading.get("kind") != "Reminder" or reading.get("change") not in (None, "", "New"):
		return []
	named = next((one.get("value") for one in reading.get("refs") or [] if one.get("kind") == "Invoice"), None)
	if not named or ctx.get("invoice_known"):
		return []
	values = {
		"subject": ctx["said"]["ask_for_invoice"].format(named, ctx.get("sender_title") or ""),
		"description": ctx["said"]["maybe_fraud"],
		"priority": "High",
		"assign_to": ctx.get("person"),
	}
	return [Action("Create", "Task", values=values, key="task|never-received", flow="onedesk.one_ai.reading.planning.make_task", sure=True, why=ctx["said"]["maybe_fraud"])]
