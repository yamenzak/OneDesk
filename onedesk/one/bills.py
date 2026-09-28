"""This workspace's own invoices from One, and One as a supplier in its books.

The invoices are Stripe's and the admin site asks for them (billing.py), so
the Plan and Credits page lists them without keeping a copy: each opens
Stripe's own page and PDF. **Payment Method** opens Stripe's billing portal,
where the card, the billing address and old receipts live.

**Into this workspace's OneBook, when asked.** Add to OneBook makes a draft
Purchase Invoice from the supplier One (the admin site's company, by its own
name, tax ID and website), with the invoice's lines and its PDF attached,
for somebody to check the expense account and submit. Never unasked: a
workspace that does not use OneBook, or books its software another way,
would find a bill it did not make.

**And OneIntake.** A Stripe receipt mailed to a mailbox OneIntake reads is
recognised by the supplier's tax ID and website, and drafted by OneIntake
itself. So on a workspace whose mailboxes OneIntake reads, the supplier is
made when the account is refreshed (`ensure_supplier`), and whichever gets
there first books it: Add to OneBook finds a bill with the same number, and
OneIntake links the mail to the bill that exists rather than making another
(one_intake/money.py, purchase).
"""

import frappe
import requests
from frappe import _
from frappe.utils import flt, nowdate

from onedesk.one import roles

#: The item every line from One is booked as, in this workspace's books.
ITEM = "One Subscription"


@frappe.whitelist()
def invoices() -> dict:
	"""The invoices, newest first, each with the bill it is in this
	workspace's books, when there is one."""
	roles.require()
	from onedesk.one import account

	said = account.ask("onedesk.one_admin.proxy.billing_invoices") or {}
	for one in said.get("invoices") or []:
		one["bill"] = _bill(one.get("number"))
	return said


@frappe.whitelist(methods=["POST"])
def payment_portal() -> dict:
	"""Stripe's billing portal, coming back to Plan and Credits."""
	roles.require()
	from onedesk.one import account

	back = frappe.utils.get_url("/desk/workspace-settings?section=plan")
	return account.ask("onedesk.one_admin.proxy.billing_portal", back=back) or {}


@frappe.whitelist(methods=["POST"])
def to_books(invoice: str) -> str:
	"""A draft Purchase Invoice from One for this invoice, or the bill that
	already books it."""
	roles.require()
	from onedesk.one import account

	said = account.ask("onedesk.one_admin.proxy.billing_invoice", invoice=invoice) or {}
	held = _bill(said.get("number"))
	if held:
		return held
	supplier = ensure_supplier(said.get("seller") or {}, said.get("currency"))
	_payable_for(supplier, said.get("currency"))
	item = _item()
	day = _day(said.get("created"))
	rows, credit = [], 0.0
	for line in said.get("lines") or []:
		amount = flt(line.get("amount"))
		if amount < 0:
			credit += -amount
			continue
		if not amount:
			continue
		quantity = max(1, int(line.get("quantity") or 1))
		rows.append(
			{
				"item_code": item,
				"item_name": (line.get("description") or ITEM)[:140],
				"description": line.get("description") or ITEM,
				"qty": quantity,
				"rate": round(amount / quantity, 2),
			}
		)
	if not rows:
		frappe.throw(_("That invoice has nothing to book."))
	expense = _expense_account()
	if expense:
		for row in rows:
			row["expense_account"] = expense
	bill = frappe.get_doc(
		{
			"doctype": "Purchase Invoice",
			"supplier": supplier,
			"bill_no": said.get("number"),
			"bill_date": day,
			"posting_date": nowdate(),
			"set_posting_time": 1,
			"currency": said.get("currency"),
			"remarks": _("From One, invoice {0}. Paid by card through Stripe.").format(said.get("number")),
			"items": rows,
		}
	)
	if credit:
		bill.apply_discount_on = "Grand Total"
		bill.discount_amount = round(credit, 2)
	bill.insert()
	_attach(bill, said)
	return bill.name


def ensure_supplier(seller: dict, currency: str | None = None) -> str | None:
	"""One, as a supplier in this workspace's books: found by tax ID or name,
	else made with what OneIntake recognises it by."""
	name = seller.get("company_name")
	if not name:
		return None
	found = (
		seller.get("tax_id") and frappe.db.get_value("Supplier", {"tax_id": seller["tax_id"]}, "name")
	) or (frappe.db.get_value("Supplier", {"supplier_name": name}, "name"))
	if found:
		return found
	supplier = frappe.get_doc(
		{
			"doctype": "Supplier",
			"supplier_name": name,
			"supplier_group": frappe.db.get_single_value("Buying Settings", "supplier_group")
			or frappe.db.get_value("Supplier Group", {"is_group": 0}, "name"),
			"supplier_type": "Company",
			"tax_id": seller.get("tax_id"),
			"website": seller.get("website"),
			"default_currency": currency,
		}
	)
	supplier.flags.ignore_permissions = True
	supplier.insert()
	return supplier.name


def keep_supplier(seller: dict | None) -> None:
	"""On refresh: when OneIntake reads any mailbox here, One is a supplier,
	so a mailed Stripe receipt is recognised. Otherwise nothing is made."""
	if not seller or not frappe.db.table_exists("Supplier"):
		return
	if not frappe.db.exists("Email Account", {"one_intake": 1}):
		return
	try:
		ensure_supplier(seller)
	except Exception:
		frappe.log_error(title="One as a supplier")


def _payable_for(supplier: str, currency: str | None) -> None:
	"""A bill in dollars goes to a payable in dollars: ERPNext will not put a
	document in one currency on a party account in another, except the
	company's own. Made once, as Creditors USD, and set on the supplier."""
	company = frappe.defaults.get_global_default("company") or frappe.db.get_value("Company", {}, "name")
	own = frappe.get_cached_value("Company", company, "default_currency")
	if not currency or currency == own:
		return
	held = frappe.get_doc("Supplier", supplier)
	if any(row.company == company for row in held.accounts):
		return
	abbr = frappe.get_cached_value("Company", company, "abbr")
	name = f"Creditors {currency} - {abbr}"
	if not frappe.db.exists("Account", name):
		parent = frappe.db.get_value(
			"Account", {"company": company, "account_type": "Payable", "is_group": 0}, "parent_account"
		)
		account = frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": f"Creditors {currency}",
				"parent_account": parent,
				"company": company,
				"account_type": "Payable",
				"account_currency": currency,
			}
		)
		account.flags.ignore_permissions = True
		account.insert()
		name = account.name
	held.append("accounts", {"company": company, "account": name})
	# ERPNext only takes a payable in the supplier's own billing currency.
	held.default_currency = held.default_currency or currency
	held.flags.ignore_permissions = True
	held.save()


#: What a software subscription is booked to, in the order a chart of
#: accounts names it. The draft says it, and somebody can change it.
EXPENSES = ("%Software%", "%Subscription%", "%Office Expense%", "%Administrative Expense%")


def _expense_account() -> str | None:
	"""Where the last bill from One went, else the first account named like
	software or office costs; else ERPNext's default (its cost of goods)."""
	last = frappe.db.sql(
		"""select item.expense_account from `tabPurchase Invoice Item` item
		join `tabPurchase Invoice` bill on bill.name = item.parent
		where item.item_code = %s and bill.docstatus = 1 order by bill.posting_date desc limit 1""",
		ITEM,
	)
	if last and last[0][0]:
		return last[0][0]
	company = frappe.defaults.get_global_default("company") or frappe.db.get_value("Company", {}, "name")
	for like in EXPENSES:
		found = frappe.db.get_value(
			"Account",
			{"company": company, "root_type": "Expense", "is_group": 0, "account_name": ["like", like]},
			"name",
		)
		if found:
			return found
	return None


def _bill(number: str | None) -> str | None:
	if not number:
		return None
	return frappe.db.get_value("Purchase Invoice", {"bill_no": number, "docstatus": ["<", 2]}, "name")


def _item() -> str:
	if not frappe.db.exists("Item", ITEM):
		item = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": ITEM,
				"item_name": ITEM,
				"item_group": frappe.db.get_value("Item Group", {"name": "Services"}, "name")
				or frappe.db.get_value("Item Group", {"is_group": 0}, "name"),
				"stock_uom": "Nos",
				"is_stock_item": 0,
				"is_purchase_item": 1,
				"is_sales_item": 0,
			}
		)
		item.flags.ignore_permissions = True
		item.insert()
	return ITEM


def _attach(bill, said: dict) -> None:
	"""The invoice's PDF on the bill, as the record of what was billed."""
	if not said.get("pdf"):
		return
	try:
		got = requests.get(said["pdf"], timeout=20)
		got.raise_for_status()
	except requests.RequestException:
		return
	# The bill stands without it: a store that cannot take the file is logged,
	# and the invoice is still one click away on the Plan and Credits page.
	mark = "one_bill_pdf"
	frappe.db.savepoint(mark)
	try:
		frappe.get_doc(
			{
				"doctype": "File",
				"file_name": f"{said.get('number') or bill.name}.pdf",
				"attached_to_doctype": "Purchase Invoice",
				"attached_to_name": bill.name,
				"is_private": 1,
				"content": got.content,
			}
		).insert(ignore_permissions=True)
		frappe.db.release_savepoint(mark)
	except Exception:
		frappe.db.rollback(save_point=mark)
		frappe.log_error(title=f"The PDF of {said.get('number')}")


def _day(stamp) -> str:
	if not stamp:
		return nowdate()
	from datetime import datetime

	return str(datetime.utcfromtimestamp(int(stamp)).date())
