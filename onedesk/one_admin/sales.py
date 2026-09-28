"""Our own customers, in our own OneCRM: somebody signing up is a lead, their
checkout is a deal, and paying makes them a customer.

The admin site is a One workspace too, and it sells One. So a signup is kept
the way any company using One keeps a sale, in ERPNext's CRM, rather than
only in the operator's tables:

* **Lead**, when the signup is taken (`signup.start`): who, the workspace
  they asked for, and the plan, with the source Website.
* **Deal**, at the same moment, because a signup is sent straight to pay: an
  Opportunity from the lead at the Checkout stage, worth a year of the plan.
  Paying wins it; a checkout left unpaid for `ABANDONED_DAYS` is lost with
  the reason Checkout Abandoned, which leaves a list somebody can follow up.
* **Customer**, when the payment lands (`signup.accept`): made from the lead
  by ERPNext's own mapping, billed in the plan's currency, and written on the
  Tenant, where our invoices find it (books.py).

Nothing here stops a signup. Every step is wrapped so a CRM that cannot take
a record logs the failure and the workspace is still made: the money has been
taken, and a missing lead is a thing to fix, not a reason to refuse.
"""

import frappe
from frappe.utils import add_days, flt, now_datetime

from onedesk.one_admin import site

#: How long a checkout waits before its deal is lost.
ABANDONED_DAYS = 7

#: Where a signup's deal waits between leaving for Stripe and paying.
CHECKOUT = "Checkout"

#: Why a deal nobody paid for was lost.
ABANDONED = "Checkout Abandoned"


def signed_up(request: str) -> None:
	"""The lead and the deal for a signup just taken."""
	if not site.is_admin():
		return
	try:
		asked = frappe.get_doc("Account Request", request)
		lead = asked.lead or _lead(asked)
		deal = asked.deal or _deal(asked, lead)
		frappe.db.set_value(
			"Account Request", asked.name, {"lead": lead, "deal": deal}, update_modified=False
		)
	except Exception:
		frappe.log_error(title=f"The lead and deal for {request}")


def paid(request: str, tenant: str) -> str | None:
	"""Win the deal and make the customer, onto the tenant."""
	if not site.is_admin():
		return None
	try:
		asked = frappe.get_doc("Account Request", request)
		customer = customer_for(tenant, lead=asked.lead)
		if asked.deal:
			_won(asked.deal, customer)
		return customer
	except Exception:
		frappe.log_error(title=f"The customer for {tenant}")
		return None


def customer_for(tenant: str, lead: str | None = None) -> str:
	"""The tenant's customer, made once: from its lead when there is one,
	from the tenant itself for a workspace that came before the CRM did."""
	held = frappe.db.get_value(
		"Tenant", tenant, ["customer", "workspace_name", "owner_email", "offering"], as_dict=True
	)
	if held.customer and frappe.db.exists("Customer", held.customer):
		return held.customer
	from onedesk.one_admin import books

	currency = frappe.db.get_value("Offering", held.offering, "currency") if held.offering else None
	currency = currency or books.CURRENCY
	if lead and frappe.db.exists("Lead", lead):
		from erpnext.crm.doctype.lead.mapper import _make_customer

		customer = _make_customer(lead, ignore_permissions=True)
	else:
		customer = frappe.new_doc("Customer")
		customer.customer_name = held.workspace_name or tenant
		customer.customer_type = "Company"
		customer.customer_group = frappe.db.get_default("Customer Group")
	customer.default_currency = currency
	receivable = books.receivable(currency)
	if receivable:
		customer.set("accounts", [{"company": books.company(), "account": receivable}])
	customer.flags.ignore_permissions = True
	customer.insert()
	if held.owner_email and not lead:
		_contact(customer.name, held.owner_email)
	frappe.db.set_value("Tenant", tenant, "customer", customer.name, update_modified=False)
	return customer.name


def abandoned() -> None:
	"""Lose the deals whose checkout nobody finished. Nightly."""
	if not site.is_admin():
		return
	cutoff = add_days(now_datetime(), -ABANDONED_DAYS)
	for request, deal in frappe.get_all(
		"Account Request",
		filters={"deal": ["is", "set"], "tenant": ["is", "not set"], "creation": ["<", cutoff]},
		fields=["name", "deal"],
		as_list=True,
	):
		try:
			held = frappe.get_doc("Opportunity", deal)
			if held.status in ("Lost", "Converted", "Closed"):
				continue
			_reason()
			held.flags.ignore_permissions = True
			held.declare_enquiry_lost(
				[{"lost_reason": ABANDONED}], [], detailed_reason=f"Signup {request} never paid."
			)
		except Exception:
			frappe.log_error(title=f"Losing the deal for {request}")
		frappe.db.commit()


def _lead(asked) -> str:
	held = frappe.db.get_value("Lead", {"email_id": asked.email}, "name")
	if held:
		return held
	plan = frappe.db.get_value("Offering", asked.offering, "label") if asked.offering else None
	lead = frappe.get_doc(
		{
			"doctype": "Lead",
			"first_name": asked.email.split("@")[0],
			"email_id": asked.email,
			"company_name": asked.workspace_name,
			"source": "Website",
			"status": "Opportunity",
			"country": asked.country,
			"notes": [{"note": f"Signed up for {asked.workspace_name} on {plan or asked.offering}."}]
			if plan or asked.offering
			else [],
		}
	)
	lead.flags.ignore_permissions = True
	lead.insert()
	return lead.name


def _deal(asked, lead: str) -> str:
	from onedesk.one_admin import books

	sold = frappe.db.get_value(
		"Offering", asked.offering, ["label", "amount", "currency", "recurring"], as_dict=True
	)
	_stage()
	deal = frappe.get_doc(
		{
			"doctype": "Opportunity",
			"opportunity_from": "Lead",
			"party_name": lead,
			"company": books.company(),
			"source": "Website",
			"sales_stage": CHECKOUT,
			"currency": (sold.currency if sold else None) or books.CURRENCY,
			"opportunity_amount": flt(sold.amount) * (12 if sold and sold.recurring else 1) if sold else 0,
			"title": f"{asked.workspace_name}: {sold.label if sold else asked.offering}",
		}
	)
	deal.flags.ignore_permissions = True
	deal.insert()
	return deal.name


def _won(deal: str, customer: str) -> None:
	from onedesk.one_crm import stages

	held = frappe.get_doc("Opportunity", deal)
	won = stages.first("Won")
	if won:
		held.sales_stage = won
	held.status = "Converted"
	held.flags.ignore_permissions = True
	held.save()
	held.add_comment("Info", f"Paid at checkout. Customer {customer}.")


def _stage() -> None:
	"""The Checkout stage, before the closing ones, on the admin site only."""
	if frappe.db.exists("Sales Stage", CHECKOUT):
		return
	from onedesk.one_crm import stages

	rows = stages.stages()
	closing = [one for one in rows if (one.one_outcome or "Open") != "Open"]
	at = min((one.one_position or 0 for one in closing), default=len(rows) + 1)
	for one in closing:
		frappe.db.set_value("Sales Stage", one.name, "one_position", (one.one_position or 0) + 1)
	frappe.get_doc(
		{
			"doctype": "Sales Stage",
			"stage_name": CHECKOUT,
			"one_position": at,
			"one_probability": 90,
			"one_outcome": "Open",
		}
	).insert(ignore_permissions=True)


def _reason() -> None:
	if not frappe.db.exists("Opportunity Lost Reason", ABANDONED):
		frappe.get_doc({"doctype": "Opportunity Lost Reason", "lost_reason": ABANDONED}).insert(
			ignore_permissions=True
		)


def _contact(customer: str, email: str) -> None:
	contact = frappe.get_doc(
		{
			"doctype": "Contact",
			"first_name": email.split("@")[0],
			"email_ids": [{"email_id": email, "is_primary": 1}],
			"links": [{"link_doctype": "Customer", "link_name": customer}],
		}
	)
	contact.insert(ignore_permissions=True)
