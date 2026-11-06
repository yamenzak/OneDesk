"""Stage 7 of Intake: money and goods, as drafts a person submits. Pure.

Every purchase document becomes a draft matched to what came before it, and
nothing is ever submitted here. Like plans.py, these answer actions and touch
nothing.
"""

from datetime import timedelta

from frappe.utils import getdate

from onedesk.one_ai.reading import deadlines
from onedesk.one_ai.reading.act import Action as _Action
from onedesk.one_project.intake import task_in

REAL = ("Action", "Information", "", None)

UNIT = "Nos"

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
		"currency": reading.get("currency"),
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


def extra_work(reading: dict, ctx: dict) -> list[Action]:
	"""A customer asking for work beyond what they ordered, as a draft
	Quotation for Extra Work on their project it names, which becomes a
	sub-project once ordered (one_project/billing.py `ordered`). Lines that
	match no item make it a proposal, as for an order."""
	if not _real(reading, ctx) or reading.get("kind") != "Change Request" or not ctx.get("customer") or not ctx.get("project"):
		return []
	items = ctx.get("customer_items") or {}
	source = reading.get("lines") or []
	rows = [
		{"item_code": items[index], "qty": float(one.get("qty") or 1), **({"rate": float(one["unit_price"])} if one.get("unit_price") is not None else {})}
		for index, one in enumerate(source)
		if items.get(index)
	]
	values = {
		"quotation_to": "Customer",
		"party_name": ctx["customer"],
		"transaction_date": ctx["today"],
		"project": ctx["project"],
		"one_extra_work": 1,
		"items": rows,
	}
	missing = len(rows) < len(source) or not rows
	return [
		Action(
			"Create",
			"Quotation",
			values={key: value for key, value in values.items() if value},
			key="books|extra",
			propose=missing,
			why=ctx["said"]["unmatched"] if missing else "",
			propose_on_error=True,
		)
	]


def goods(reading: dict, ctx: dict) -> list[Action]:
	"""A supplier's delivery note, as a draft Purchase Receipt against the
	order it delivers, for what the note says came. A line that matches no
	item makes it a proposal."""
	if not _real(reading, ctx) or reading.get("kind") != "Delivery Note" or not ctx.get("purchase_order"):
		return []
	items = ctx.get("items") or {}
	source = reading.get("lines") or []
	delivered = {}
	for index, one in enumerate(source):
		if items.get(index):
			delivered[items[index]] = delivered.get(items[index], 0) + float(one.get("qty") or 0)
	missing = any(not items.get(index) for index in range(len(source)))
	values = {"order": ctx["purchase_order"], "supplier_delivery_note": reading.get("number"), "delivered": delivered}
	return [Action("Create", "Purchase Receipt", values={key: value for key, value in values.items() if value}, key="books|receipt", flow="onedesk.one_ai.reading.planning.receipt_from_order", propose=missing, why=ctx["said"]["unmatched"] if missing else "", propose_on_error=True)]


def unordered(reading: dict, ctx: dict) -> list[Action]:
	"""A delivery from a known supplier that no order of ours asked for: a
	task to check it before anybody signs for it or pays."""
	if not _real(reading, ctx) or reading.get("kind") != "Delivery Note" or ctx.get("purchase_order") or not ctx.get("supplier") or reading.get("change") not in (None, "", "New"):
		return []
	values = {
		"subject": ctx["said"]["unordered"].format(ctx["supplier"]),
		"description": ctx["said"]["see_document"],
		"exp_end_date": ctx["today"],
		"one_about_doctype": "Supplier",
		"one_about": ctx["supplier"],
		"assign_to": ctx.get("person"),
		"project": task_in(ctx.get("project"), ctx["today"]),
	}
	return [_Action("Create", "Task", values=values, key="task|unordered", flow="onedesk.one_ai.reading.planning.make_task", sure=True)]


def _each(line: dict) -> float:
	"""A line's price for one: its unit price, or its amount over how many."""
	if line.get("unit_price") is not None:
		return float(line["unit_price"])
	return float(line.get("amount") or 0) / (float(line.get("qty") or 1) or 1)


def quotation(reading: dict, ctx: dict) -> list[Action]:
	"""A supplier's offer, as a Supplier Quotation when every line is an item."""
	if not _real(reading, ctx) or reading.get("kind") != "Offer" or not ctx.get("supplier"):
		return []
	items = ctx.get("items") or {}
	source = reading.get("lines") or []
	if not source or len(items) < len(source):
		return []
	rows = [{"item_code": items[index], "qty": float(one.get("qty") or 1), "rate": _each(one)} for index, one in enumerate(source)]
	valid = next((str(one["date"]) for one in reading.get("dates") or [] if one.get("what") == "Valid Until" and one.get("date")), None)
	values = {"supplier": ctx["supplier"], "transaction_date": ctx["today"], "valid_till": valid, "items": rows}
	return [Action("Create", "Supplier Quotation", values={k: v for k, v in values.items() if v}, key="books|quotation", propose_on_error=True)]


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


def contract(reading: dict, ctx: dict) -> list[Action]:
	"""A contract with a customer or supplier, as ERPNext's Contract."""
	party = ctx.get("contract_party")
	if not _real(reading, ctx) or reading.get("kind") != "Contract" or not party:
		return []
	dates = {one.get("what"): str(one.get("date")) for one in reading.get("dates") or [] if one.get("date")}
	end = dates.get("Valid Until") or dates.get("Period End")
	notice = deadlines.period(reading.get("notice_period"))
	cancel_by = str(deadlines.before(getdate(end), *notice)) if end and notice else None
	values = {
		"party_type": party[0],
		"party_name": party[1],
		"start_date": dates.get("Valid From") or dates.get("Period Start") or reading.get("issued_on") or ctx["today"],
		"end_date": end,
		"one_notice_period": reading.get("notice_period"),
		"one_cancel_by": cancel_by,
		"contract_terms": reading.get("summary") if reading.get("sensitivity") in (None, "", "Ordinary") else ctx["said"]["see_document"],
	}
	out = [Action("Create", "Contract", values={k: v for k, v in values.items() if v}, key="books|contract")]
	if cancel_by:
		remind = str(max(getdate(cancel_by) - timedelta(days=30), getdate(ctx["today"])))
		out.append(
			_Action(
				"Create",
				"Task",
				values={"subject": ctx["said"]["decide_cancel"].format(party[1], cancel_by), "exp_end_date": remind, "one_about_doctype": party[0], "one_about": party[1], "assign_to": ctx.get("person")},
				key="task|contract",
				flow="onedesk.one_ai.reading.planning.make_task",
				sure=True,
			)
		)
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


def plan(reading: dict, ctx: dict) -> list[Action]:
	return purchase(reading, ctx) + sales_order(reading, ctx) + extra_work(reading, ctx) + goods(reading, ctx) + unordered(reading, ctx) + quotation(reading, ctx) + payment(reading, ctx) + bank(reading, ctx) + contract(reading, ctx) + never_received(reading, ctx)
