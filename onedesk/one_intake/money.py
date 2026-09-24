"""Stage 7 of Intake: money and goods, as drafts a person submits. Pure.

A company keeps books, so every purchase document becomes a draft matched to
what came before it: an invoice to its Purchase Order, a supplier's delivery
note to a Purchase Receipt against the order, a credit note to a return
against the invoice it credits (docs/INTAKE.md §3.2). An order from a
customer becomes a draft Sales Order, a payment advice a draft Payment Entry
against our invoice, a supplier's quote a Supplier Quotation, a contract
ERPNext's Contract. A bank statement's lines become Bank Transactions, which
are not postings. Nothing is ever submitted here: posting stays a person's
act, in Ready to submit (drafts.py).

Every draft is written as the person OneAI acts for, since ERPNext asks the
signed-in user about every account a draft touches; the OneAI mark still
says who made it.

A household does not keep books (Intake Settings' Make Drafts in the Books is
off): nothing here runs, and Spending reads the same readings.

Like plans.py, these take a reading and what planning found out and answer
actions; they touch nothing.
"""

from datetime import timedelta

from frappe.utils import getdate

from onedesk.one_intake.act import Action as _Action

REAL = ("Action", "Information", "", None)

#: A line with no item is booked by name, in this unit.
UNIT = "Nos"

#: How long after an order a customer is assumed to want it, when the order
#: gives no date.
DELIVERY_DAYS = 7


def Action(*args, **kwargs) -> _Action:
	"""Every money action is written as the person OneAI acts for: ERPNext
	checks the signed-in user's access to each account a draft touches."""
	return _Action(*args, **{**kwargs, "as_person": True})


def _real(reading: dict, ctx: dict) -> bool:
	return bool(ctx.get("books")) and reading.get("verdict") in REAL and not ctx.get("history") and ctx.get("direction") != "Sent"


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
			# 250 kWh at 0.28304 rounds to 70.00 in a currency of cents: the
			# line is booked at what it cost, and says how that was made.
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


def purchase(reading: dict, ctx: dict) -> list[Action]:
	"""An invoice, a receipt the company paid or a credit note, from a known
	supplier, as a draft."""
	kind = reading.get("kind")
	if not _real(reading, ctx) or kind not in ("Invoice", "Receipt", "Credit Note") or not ctx.get("supplier") or ctx.get("sender_is_colleague"):
		return []
	if ctx.get("existing_invoice"):
		# Somebody booked it first: the document goes there, and nothing is made.
		return [Action("Link", "Purchase Invoice", ctx["existing_invoice"], {"file": ctx.get("file")}, key="books|existing", sure=True)] if ctx.get("file") else []
	day, moved = posting_day(ctx["today"], ctx.get("locked"))
	remarks = [ctx["said"]["moved"].format(ctx["locked"])] if moved else []
	if reading.get("paid_how") == "Direct Debit":
		remarks.append(ctx["said"]["direct_debit"])
	elif reading.get("paid_how") == "Already Paid" or kind == "Receipt":
		remarks.append(ctx["said"]["paid"])
	due = next((str(one["date"]) for one in reading.get("dates") or [] if one.get("what") == "Due" and one.get("date")), None)
	head = {
		"supplier": ctx["supplier"],
		"bill_no": reading.get("number"),
		"bill_date": reading.get("issued_on"),
		"posting_date": day,
		"set_posting_time": 1,
		"due_date": due if due and due >= day else None,
		"currency": reading.get("currency"),
		"remarks": " ".join(remarks) or None,
	}
	head = {key: value for key, value in head.items() if value}
	if kind == "Credit Note":
		if ctx.get("original_invoice"):
			return [Action("Create", "Purchase Invoice", values={"against": ctx["original_invoice"], **head}, key="books|credit", flow="onedesk.one_intake.planning.debit_note")]
		return [Action("Create", "Purchase Invoice", values={**head, "is_return": 1, "items": [{**row, "qty": -abs(row["qty"])} for row in lines(reading, ctx.get("items") or {}, ctx.get("expense_account"))]}, key="books|credit", propose=True, why=ctx["said"]["no_original"])]
	if ctx.get("purchase_order"):
		return [Action("Create", "Purchase Invoice", values={"order": ctx["purchase_order"], **head}, key="books|invoice", flow="onedesk.one_intake.planning.invoice_from_order", propose_on_error=True)]
	rows = lines(reading, ctx.get("items") or {}, ctx.get("expense_account"))
	if not rows:
		return []
	return [Action("Create", "Purchase Invoice", values={**head, "items": rows}, key="books|invoice", propose_on_error=True)]


def sales_order(reading: dict, ctx: dict) -> list[Action]:
	"""An order from a customer, as a draft Sales Order. Lines that match no
	item make it a proposal, since a Sales Order row needs one."""
	if not _real(reading, ctx) or reading.get("kind") != "Order" or not ctx.get("customer"):
		return []
	items = ctx.get("customer_items") or {}
	source = reading.get("lines") or []
	rows = [
		{"item_code": items[index], "qty": float(one.get("qty") or 1), **({"rate": float(one["unit_price"])} if one.get("unit_price") is not None else {})}
		for index, one in enumerate(source)
		if items.get(index)
	]
	when = next((str(one["date"]) for one in reading.get("dates") or [] if one.get("what") in ("Due", "Deadline") and one.get("date")), None)
	values = {
		"customer": ctx["customer"],
		"transaction_date": ctx["today"],
		"delivery_date": when or str(getdate(ctx["today"]) + timedelta(days=DELIVERY_DAYS)),
		"po_no": reading.get("number"),
		"po_date": reading.get("issued_on"),
		"items": rows,
	}
	missing = len(rows) < len(source) or not rows
	return [
		Action(
			"Create",
			"Sales Order",
			values={key: value for key, value in values.items() if value},
			key="books|order",
			propose=missing,
			why=ctx["said"]["unmatched"] if missing else "",
			propose_on_error=True,
		)
	]


def goods(reading: dict, ctx: dict) -> list[Action]:
	"""A supplier's delivery note, as a draft Purchase Receipt against the
	order it delivers."""
	if not _real(reading, ctx) or reading.get("kind") != "Delivery Note" or not ctx.get("purchase_order"):
		return []
	return [Action("Create", "Purchase Receipt", values={"order": ctx["purchase_order"], "supplier_delivery_note": reading.get("number")}, key="books|receipt", flow="onedesk.one_intake.planning.receipt_from_order", propose_on_error=True)]


def quotation(reading: dict, ctx: dict) -> list[Action]:
	"""A supplier's offer, as a Supplier Quotation when every line is an item."""
	if not _real(reading, ctx) or reading.get("kind") != "Offer" or not ctx.get("supplier"):
		return []
	items = ctx.get("items") or {}
	source = reading.get("lines") or []
	if not source or len(items) < len(source):
		return []
	rows = [{"item_code": items[index], "qty": float(one.get("qty") or 1), "rate": float(one.get("unit_price") or one.get("amount") or 0)} for index, one in enumerate(source)]
	valid = next((str(one["date"]) for one in reading.get("dates") or [] if one.get("what") == "Valid Until" and one.get("date")), None)
	values = {"supplier": ctx["supplier"], "transaction_date": ctx["today"], "valid_till": valid, "items": rows}
	return [Action("Create", "Supplier Quotation", values={k: v for k, v in values.items() if v}, key="books|quotation", propose_on_error=True)]


def payment(reading: dict, ctx: dict) -> list[Action]:
	"""A customer's payment advice, as a draft Payment Entry against our
	invoice it names."""
	if not _real(reading, ctx) or reading.get("kind") != "Payment Advice" or not ctx.get("sales_invoice"):
		return []
	values = {"invoice": ctx["sales_invoice"], "amount": reading.get("gross"), "reference_no": reading.get("payment_reference") or reading.get("number"), "reference_date": reading.get("issued_on") or ctx["today"]}
	return [Action("Create", "Payment Entry", values={k: v for k, v in values.items() if v}, key="books|payment", flow="onedesk.one_intake.planning.payment_for", propose_on_error=True)]


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
		out.append(Action("Create", "Bank Transaction", values={k: v for k, v in values.items() if v not in (None, "")}, key=f"books|bank|{one.get('key')}", flow="onedesk.one_intake.planning.bank_line", sure=True))
	return out


def contract(reading: dict, ctx: dict) -> list[Action]:
	"""A contract with a customer or supplier, as ERPNext's Contract."""
	party = ctx.get("contract_party")
	if not _real(reading, ctx) or reading.get("kind") != "Contract" or not party:
		return []
	dates = {one.get("what"): str(one.get("date")) for one in reading.get("dates") or [] if one.get("date")}
	values = {
		"party_type": party[0],
		"party_name": party[1],
		"start_date": dates.get("Valid From") or dates.get("Period Start") or reading.get("issued_on") or ctx["today"],
		"end_date": dates.get("Valid Until") or dates.get("Period End"),
		"contract_terms": reading.get("summary") if reading.get("sensitivity") in (None, "", "Ordinary") else ctx["said"]["see_document"],
	}
	return [Action("Create", "Contract", values={k: v for k, v in values.items() if v}, key="books|contract")]


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
	return [Action("Create", "Task", values=values, key="task|never-received", flow="onedesk.one_intake.planning.make_task", sure=True, why=ctx["said"]["maybe_fraud"])]


def plan(reading: dict, ctx: dict) -> list[Action]:
	return purchase(reading, ctx) + sales_order(reading, ctx) + goods(reading, ctx) + quotation(reading, ctx) + payment(reading, ctx) + bank(reading, ctx) + contract(reading, ctx) + never_received(reading, ctx)
