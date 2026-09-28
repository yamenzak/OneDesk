"""Our own books, kept in our own OneBook from what Stripe charges.

The admin site is a One workspace and One is what it sells, so every sale is
booked the way any company using One books one:

* **An Item per Offering** (`item_for`), a service under One Subscriptions,
  kept in step with the price list (`synced`, on the Offering's save).
* **A Sales Invoice per paid Stripe invoice** (`invoiced`): the plan, each
  add-on at its quantity, and the prorated lines Stripe writes when a plan
  changes part way through a month. A proration credit (a negative line) is
  taken off as the invoice's discount, since an invoice line cannot be less
  than nothing. A credit pack is an invoice of one line (`pack_bought`).
* **A Payment Entry** into the Stripe account, for what Stripe collected,
  referenced by the charge.
* **Stripe's fee** as a Journal Entry from the Stripe account to Stripe Fees,
  read from the charge's balance transaction.
* **A refund** as a credit note against the invoice, paid back out of the
  Stripe account (`refunded`).

The customer is the tenant's (sales.customer_for). Stripe charges in the
price list's currency, US dollars, and the company keeps its books in its
own, so the invoice and the payment are in dollars at the day's exchange rate
into a receivable and a Stripe account in dollars, both made here once
(`ensure`). ERPNext does the conversion; nothing here multiplies by a rate.

**Booked once.** Each invoice carries the Stripe object it came from
(`one_stripe_invoice`), so a webhook Stripe redelivers finds it already
there, and `catch_up` books any paid invoice the webhook missed.

**Never in the way.** A failure here is logged and left for `catch_up`; the
webhook still moves the workspace, because the customer has paid either way.
"""

import frappe
from frappe.utils import flt, getdate, nowdate

from onedesk.one_admin import site

#: What Stripe charges in: the price list's currency (offerings.CURRENCY).
CURRENCY = "USD"

#: The item group our offerings are sold under.
GROUP = "One Subscriptions"

#: The account names made once, per currency where it matters.
STRIPE = "Stripe {0}"
RECEIVABLE = "Debtors {0}"
FEES = "Stripe Fees"
MODE = "Stripe"

#: How far back catch_up looks for paid invoices the webhook did not book.
CATCH_UP_DAYS = 35


def company() -> str:
	return (
		frappe.defaults.get_global_default("company") or frappe.get_all("Company", pluck="name", limit=1)[0]
	)


def _abbr() -> str:
	return frappe.get_cached_value("Company", company(), "abbr")


def ensure(*_args) -> None:
	"""The accounts, the mode of payment and the item group, once. On the
	admin site, after migrate."""
	if not site.is_admin() or not frappe.db.table_exists("Account") or not frappe.get_all("Company", limit=1):
		return
	stripe_account(CURRENCY)
	receivable(CURRENCY)
	fees_account()
	if not frappe.db.exists("Item Group", GROUP):
		frappe.get_doc(
			{"doctype": "Item Group", "item_group_name": GROUP, "parent_item_group": "All Item Groups"}
		).insert(ignore_permissions=True)
	for offering in frappe.get_all("Offering", pluck="name"):
		item_for(offering)


# ------------------------------------------------------------------ accounts


def _account(name: str, parent: str | None, **values) -> str | None:
	full = f"{name} - {_abbr()}"
	if frappe.db.exists("Account", full):
		return full
	if not parent:
		return None
	doc = frappe.get_doc(
		{"doctype": "Account", "account_name": name, "parent_account": parent, "company": company(), **values}
	)
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc.name


def _group(account_type: str | None = None, root: str | None = None, named: str | None = None) -> str | None:
	"""A group account to put a new one under: the parent of one of this
	type, or a group by name, or the root of its kind."""
	if account_type:
		held = frappe.db.get_value(
			"Account", {"company": company(), "account_type": account_type, "is_group": 0}, "parent_account"
		)
		if held:
			return held
	if named:
		held = frappe.db.get_value(
			"Account", {"company": company(), "account_name": named, "is_group": 1}, "name"
		)
		if held:
			return held
	if root:
		return frappe.db.get_value(
			"Account",
			{"company": company(), "root_type": root, "is_group": 1, "parent_account": ["in", ("", None)]},
			"name",
		)
	return None


def stripe_account(currency: str = CURRENCY) -> str | None:
	"""Where Stripe holds what it collected before a payout: a bank account."""
	return _account(
		STRIPE.format(currency),
		_group("Bank"),
		account_type="Bank",
		account_currency=currency,
	)


def receivable(currency: str = CURRENCY) -> str | None:
	"""What a customer billed in this currency owes."""
	if currency == frappe.get_cached_value("Company", company(), "default_currency"):
		return frappe.get_cached_value("Company", company(), "default_receivable_account")
	return _account(
		RECEIVABLE.format(currency),
		_group("Receivable"),
		account_type="Receivable",
		account_currency=currency,
	)


def fees_account() -> str | None:
	return _account(FEES, _group(named="Indirect Expenses", root="Expense"), account_type="Expense Account")


def _mode() -> str:
	if not frappe.db.exists("Mode of Payment", MODE):
		frappe.get_doc(
			{
				"doctype": "Mode of Payment",
				"mode_of_payment": MODE,
				"type": "Bank",
				"accounts": [{"company": company(), "default_account": stripe_account()}],
			}
		).insert(ignore_permissions=True)
	return MODE


# ------------------------------------------------------------------ items


def item_code(offering: str) -> str:
	return f"ONE-{offering}".upper()


def item_for(offering: str) -> str:
	"""The Item an offering is invoiced as, made once and kept in step."""
	sold = frappe.db.get_value(
		"Offering", offering, ["label", "kind", "amount", "enabled", "description"], as_dict=True
	)
	code = item_code(offering)
	values = {
		"item_name": sold.label or offering,
		"description": sold.description or sold.label or offering,
		"disabled": 0 if sold.enabled else 1,
		"standard_rate": flt(sold.amount),
	}
	if frappe.db.exists("Item", code):
		held = frappe.get_doc("Item", code)
		changed = {
			key: value for key, value in values.items() if key != "standard_rate" and held.get(key) != value
		}
		if changed:
			held.update(changed)
			held.flags.ignore_permissions = True
			held.save()
		return code
	if not frappe.db.exists("Item Group", GROUP):
		ensure()
	item = frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": code,
			"item_group": GROUP,
			"stock_uom": "Nos",
			"is_stock_item": 0,
			"include_item_in_manufacturing": 0,
			"is_sales_item": 1,
			"is_purchase_item": 0,
			**values,
		}
	)
	item.flags.ignore_permissions = True
	item.insert()
	return code


def synced(doc, method=None) -> None:
	"""An Offering saved: its Item follows, on the admin site."""
	if site.is_admin():
		try:
			item_for(doc.name)
		except Exception:
			frappe.log_error(title=f"The item for {doc.name}")


# ------------------------------------------------------------------ invoices


def invoiced(invoice: dict) -> str | None:
	"""A paid Stripe invoice, booked: the Sales Invoice, its payment and the
	fee. Returns the Sales Invoice, or None when there is nothing to book."""
	site.require_admin()
	held = _booked(invoice.get("id"))
	if held:
		return held
	paid = flt(invoice.get("amount_paid")) / 100
	if paid <= 0:
		# A trial's zero invoice, or one settled from Stripe credit: no money moved.
		return None
	tenant = frappe.db.get_value("Tenant", {"stripe_customer": invoice.get("customer")}, "name")
	if not tenant:
		return None
	from onedesk.one_admin import sales

	customer = sales.customer_for(tenant)
	currency = (invoice.get("currency") or CURRENCY).upper()
	day = _day(invoice.get("status_transitions", {}).get("paid_at") or invoice.get("created"))
	lines, credit = [], 0.0
	for line in (invoice.get("lines") or {}).get("data") or []:
		amount = flt(line.get("amount")) / 100
		if amount < 0:
			credit += -amount
			continue
		quantity = max(1, int(line.get("quantity") or 1))
		lines.append(
			{
				"item_code": _item_for_price(line),
				"description": line.get("description") or "",
				"qty": quantity,
				"rate": round(amount / quantity, 2),
			}
		)
	if not lines:
		return None
	si = _invoice(customer, currency, day, lines, invoice.get("id"), credit, tenant)
	_pay(si, paid, invoice.get("charge") or invoice.get("id"), day)
	_fee(invoice.get("charge"), currency, day, si.name)
	return si.name


def pack_bought(session: dict) -> str | None:
	"""A credit pack's checkout, booked the same way: one line."""
	site.require_admin()
	held = _booked(session.get("id"))
	if held:
		return held
	meta = session.get("metadata") or {}
	tenant, pack = meta.get("tenant"), meta.get("pack")
	paid = flt(session.get("amount_total")) / 100
	if not tenant or not pack or paid <= 0:
		return None
	from onedesk.one_admin import sales

	customer = sales.customer_for(tenant)
	currency = (session.get("currency") or CURRENCY).upper()
	day = _day(session.get("created"))
	si = _invoice(
		customer,
		currency,
		day,
		[{"item_code": item_for(pack), "qty": 1, "rate": paid}],
		session.get("id"),
		0,
		tenant,
	)
	charge = _charge_of(session.get("payment_intent"))
	_pay(si, paid, charge or session.get("id"), day)
	_fee(charge, currency, day, si.name)
	return si.name


def refunded(charge: dict) -> str | None:
	"""A refund on a charge we booked, as a credit note paid back out of Stripe.
	Only what is new since the last refund on it is credited."""
	site.require_admin()
	pe = frappe.db.get_value("Payment Entry", {"reference_no": charge.get("id"), "docstatus": 1}, "name")
	si = (
		frappe.db.get_value(
			"Payment Entry Reference", {"parent": pe, "reference_doctype": "Sales Invoice"}, "reference_name"
		)
		if pe
		else None
	)
	if not si:
		return None
	refunded_total = flt(charge.get("amount_refunded")) / 100
	credited = -flt(
		frappe.db.sql(
			"select coalesce(sum(grand_total), 0) from `tabSales Invoice` where return_against=%s and docstatus=1",
			si,
		)[0][0]
	)
	amount = round(refunded_total - credited, 2)
	if amount <= 0:
		return None
	original = frappe.get_doc("Sales Invoice", si)
	note = frappe.get_doc(
		{
			"doctype": "Sales Invoice",
			"customer": original.customer,
			"company": original.company,
			"currency": original.currency,
			"debit_to": original.debit_to,
			"is_return": 1,
			"return_against": si,
			"posting_date": nowdate(),
			"set_posting_time": 1,
			"one_stripe_invoice": f"{charge.get('id')}:refund:{refunded_total}",
			"items": [{"item_code": original.items[0].item_code, "qty": -1, "rate": amount}],
		}
	)
	note.flags.ignore_permissions = True
	note.insert()
	note.submit()
	_pay(note, -amount, f"{charge.get('id')}:refund", getdate(nowdate()))
	return note.name


def catch_up() -> None:
	"""Book any invoice Stripe says was paid that the webhook did not. Nightly."""
	if not site.is_admin():
		return
	from onedesk.one_admin import faults, stripe

	since = int(frappe.utils.add_days(frappe.utils.now_datetime(), -CATCH_UP_DAYS).timestamp())
	try:
		found = (
			stripe.fetch("invoices", {"status": "paid", "created[gte]": since, "limit": 100}).get("data")
			or []
		)
	except (faults.Refused, frappe.ValidationError):
		return
	for invoice in found:
		try:
			invoiced(invoice)
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			frappe.log_error(title=f"Booking {invoice.get('id')}")


# ------------------------------------------------------------------ the parts


def _booked(stripe_id: str | None) -> str | None:
	return (
		frappe.db.get_value("Sales Invoice", {"one_stripe_invoice": stripe_id, "docstatus": 1}, "name")
		if stripe_id
		else None
	)


def _item_for_price(line: dict) -> str:
	price = (line.get("price") or {}).get("id") or (line.get("plan") or {}).get("id")
	offering = (frappe.db.get_value("Offering", {"stripe_price": price}, "name") if price else None) or (
		(line.get("price") or {}).get("metadata") or {}
	).get("offering")
	if not offering and price:
		# A customer still on a price the offering has moved on from: the item
		# is the offering whose Tenant Add-on or plan carries it, by metadata.
		offering = frappe.db.get_value("Offering", {"key": price}, "name")
	return item_for(offering) if offering else _unknown()


def _unknown() -> str:
	"""An item for a line no offering claims, so the invoice still balances."""
	code = "ONE-OTHER"
	if not frappe.db.exists("Item", code):
		if not frappe.db.exists("Item Group", GROUP):
			ensure()
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": code,
				"item_name": "One",
				"item_group": GROUP,
				"stock_uom": "Nos",
				"is_stock_item": 0,
				"is_sales_item": 1,
			}
		).insert(ignore_permissions=True)
	return code


def _invoice(customer, currency, day, lines, stripe_id, credit, tenant):
	si = frappe.get_doc(
		{
			"doctype": "Sales Invoice",
			"customer": customer,
			"company": company(),
			"currency": currency,
			"debit_to": receivable(currency),
			"posting_date": day,
			"set_posting_time": 1,
			"due_date": day,
			"one_stripe_invoice": stripe_id,
			"remarks": f"Stripe {stripe_id} for workspace {tenant}.",
			"items": lines,
		}
	)
	if credit:
		si.apply_discount_on = "Grand Total"
		si.discount_amount = round(credit, 2)
	si.flags.ignore_permissions = True
	si.insert()
	si.submit()
	return si


def _pay(si, amount: float, reference: str, day) -> str:
	"""The money into the Stripe account against this invoice, or back out of
	it for a credit note."""
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	# The Stripe account handed to ERPNext's own builder, which then sets its
	# currency, the amounts either side and the exchange rates itself.
	# A credit note's own outstanding (negative) is what goes back out.
	pe = get_payment_entry(
		"Sales Invoice",
		si.name,
		party_amount=amount if amount > 0 else None,
		bank_account=stripe_account(si.currency),
	)
	pe.mode_of_payment = _mode()
	pe.reference_no = reference
	pe.reference_date = day
	pe.posting_date = day
	pe.flags.ignore_permissions = True
	pe.insert()
	pe.submit()
	return pe.name


def _fee(charge: str | None, currency: str, day, si: str) -> str | None:
	"""Stripe's fee on a charge, from the Stripe account to Stripe Fees."""
	if not charge or not str(charge).startswith("ch_"):
		return None
	from onedesk.one_admin import faults, stripe

	try:
		held = stripe.fetch(f"charges/{charge}", {"expand[]": "balance_transaction"})
	except (faults.Refused, frappe.ValidationError):
		return None
	fee = flt(((held.get("balance_transaction") or {}).get("fee")) or 0) / 100
	if fee <= 0:
		return None
	from erpnext.setup.utils import get_exchange_rate

	rate = (
		get_exchange_rate(currency, frappe.get_cached_value("Company", company(), "default_currency"), day)
		or 1
	)
	je = frappe.get_doc(
		{
			"doctype": "Journal Entry",
			"company": company(),
			"posting_date": day,
			"multi_currency": 1,
			"cheque_no": charge,
			"cheque_date": day,
			"user_remark": f"Stripe fee on {charge} for {si}.",
			"accounts": [
				{"account": fees_account(), "debit_in_account_currency": round(fee * rate, 2)},
				{
					"account": stripe_account(currency),
					"credit_in_account_currency": fee,
					"exchange_rate": rate,
				},
			],
		}
	)
	je.flags.ignore_permissions = True
	je.insert()
	je.submit()
	return je.name


def _charge_of(payment_intent: str | None) -> str | None:
	if not payment_intent:
		return None
	from onedesk.one_admin import faults, stripe

	try:
		return stripe.fetch(f"payment_intents/{payment_intent}").get("latest_charge")
	except (faults.Refused, frappe.ValidationError):
		return None


def _day(stamp) -> str:
	if not stamp:
		return nowdate()
	from datetime import datetime

	return str(datetime.utcfromtimestamp(int(stamp)).date())
