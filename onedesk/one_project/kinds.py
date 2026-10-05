"""A project's kind: how it's paid for, which decides what it asks for when it
is made and what its page shows (docs/PROJECT-PAGE.md).

- **Fixed Price**: an agreed price, billed as the work gets done. Its
  contract is the customer's Sales Order, made with the project (`make`), so
  Bill Progress works from the first day (progress.py).
- **Time and Materials**: billed by the hour at agreed rates, plus what's
  bought for it (billing.py's Invoice Time).
- **Retainer**: a monthly fee for a set number of hours (`one_monthly_fee`,
  `one_monthly_hours`).
- **Internal**: no customer; a budget and the work.

The kind is `one_kind` on Project. A project made without one, by ERPNext,
HR or an import, is given the kind its records say (`guess`, `fill`), as
`patches/kinds.py` did for the projects made before kinds existed.
"""

from typing import Annotated

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate, nowdate

from onedesk.one_book.currency import bill_in, billed_in

FIXED = "Fixed Price"
TIME = "Time and Materials"
RETAINER = "Retainer"
INTERNAL = "Internal"
KINDS = (FIXED, TIME, RETAINER, INTERNAL)


def guess(has_order: bool, has_billable_time: bool, customer: str | None) -> str:
	"""The kind a project's records say it is. Pure."""
	if has_order:
		return FIXED
	if has_billable_time or customer:
		return TIME
	return INTERNAL


def fill(doc, method=None) -> None:
	"""Project before_validate: a project made without a kind gets the one its
	records say."""
	if doc.get("one_kind"):
		return
	name = None if doc.is_new() else doc.name
	has_order = bool(doc.get("sales_order")) or bool(
		name and frappe.db.exists("Sales Order", {"project": name, "docstatus": 1})
	)
	billable = bool(name and frappe.db.exists("Timesheet Detail", {"project": name, "is_billable": 1}))
	doc.one_kind = guess(has_order, billable, doc.get("customer"))


@frappe.whitelist(methods=["POST"])
def make(values: Annotated[dict | str, "What the New Project dialog asked for."]) -> str:
	"""Make a project of a kind, with what that kind needs; for Fixed Price,
	its contract too. Returns the project's name."""
	values = frappe._dict(frappe.parse_json(values))
	frappe.has_permission("Project", "create", throw=True)
	kind = values.kind
	if kind not in KINDS:
		frappe.throw(_("Pick what kind of project this is."))
	if kind != INTERNAL and not values.client:
		frappe.throw(_("Pick the customer."))
	contract = flt(values.contract)
	if kind == FIXED and contract:
		frappe.has_permission("Sales Order", "create", throw=True)
		if not values.item:
			frappe.throw(_("Pick the item to bill the contract as."))

	project = frappe.new_doc("Project")
	project.update(
		{
			"project_name": (values.title or "").strip(),
			"one_kind": kind,
			"customer": values.client if kind != INTERNAL else None,
			"expected_start_date": values.starts,
			"expected_end_date": values.ends,
			"one_manager": values.manager or frappe.session.user,
			"project_template": values.template,
			"estimated_costing": flt(values.budget) if kind in (TIME, INTERNAL) else 0,
			"one_monthly_fee": flt(values.monthly_fee) if kind == RETAINER else 0,
			"one_monthly_hours": flt(values.monthly_hours) if kind == RETAINER else 0,
			"one_markup": flt(values.markup) if kind == TIME else 0,
			# How its time is counted, and where (hours.py).
			"one_time": values.time,
			"one_site": values.site,
		}
	)
	if values.parent:
		project.one_parent = values.parent
	project.insert()

	if kind == FIXED and contract:
		order = _contract(project, values, contract)
		project.db_set("sales_order", order)
	return project.name


def _contract(project, values, contract: float) -> str:
	"""The customer's Sales Order for the contract value, submitted: the
	contract Bill Progress bills against."""
	start = getdate(values.starts or nowdate())
	ends = getdate(values.ends) if values.ends else add_days(start, 30)
	order = frappe.new_doc("Sales Order")
	order.company = project.company
	# The contract value is in the customer's own currency, as the order is.
	bill_in(order, "Customer", project.customer)
	order.update(
		{
			"customer": project.customer,
			"project": project.name,
			"transaction_date": nowdate(),
			"delivery_date": max(ends, getdate(nowdate())),
			"one_retention": flt(values.retention),
			"one_retention_due": values.retention_due if flt(values.retention) else None,
			"one_retention_handover": flt(values.retention_handover) if flt(values.retention) else 0,
		}
	)
	order.append(
		"items",
		{
			"item_code": values.item,
			"qty": 1,
			"rate": contract,
			"delivery_date": order.delivery_date,
			"description": project.project_name,
		},
	)
	order.insert()
	order.submit()
	return order.name


@frappe.whitelist(methods=["POST"])
def add_contract(
	project: Annotated[str, "The project."],
	contract: Annotated[float, "The contract value."],
	item: Annotated[str, "The item to bill it as."],
	retention: Annotated[float | None, "Retention, in percent."] = None,
	retention_due: Annotated[str | None, "When the retention is due."] = None,
	retention_handover: Annotated[float | None, "The share of the retention released at handover."] = None,
) -> str:
	"""A Fixed Price project's contract, made after the project: the same
	submitted Sales Order the New Project dialog makes. Returns its name."""
	from onedesk.one_project.view import contract as ordered

	doc = frappe.get_doc("Project", project)
	frappe.has_permission("Project", "write", doc=doc, throw=True)
	frappe.has_permission("Sales Order", "create", throw=True)
	if not doc.customer:
		frappe.throw(_("Pick the project's customer first."))
	if flt(contract) <= 0:
		frappe.throw(_("Enter the contract value."))
	if not item:
		frappe.throw(_("Pick the item to bill the contract as."))
	if ordered(doc):
		frappe.throw(_("{0} has a contract already. Change it on its sales order.").format(doc.project_name))
	values = frappe._dict(
		item=item,
		retention=retention,
		retention_due=retention_due,
		retention_handover=retention_handover,
		starts=doc.expected_start_date,
		ends=doc.expected_end_date,
	)
	order = _contract(doc, values, flt(contract))
	doc.db_set("sales_order", order)
	return order


#: The item a contract is billed as when the workspace has none of its own:
#: a service in Lump Sum, so Bill Progress can bill it in parts.
CONTRACT_ITEM = "Contract Work"


@frappe.whitelist()
@frappe.read_only()
def defaults(customer: Annotated[str | None, "The customer, for their currency."] = None) -> dict:
	"""What the New Project and Add Contract dialogs start with: the item the
	last project's contract was billed as, or Contract Work, the currency the
	customer is billed in, and how the workspace counts time."""
	found = frappe.get_all(
		"Sales Order Item",
		filters={"docstatus": 1, "project": ["is", "set"]},
		fields=["item_code"],
		order_by="creation desc",
		limit=1,
	)
	item = found[0].item_code if found else None
	if not item and frappe.db.exists("Item", CONTRACT_ITEM):
		item = CONTRACT_ITEM
	currency = None
	if customer and frappe.has_permission("Customer", "read", doc=customer):
		currency = billed_in("Customer", customer)
	from onedesk.one_project.hours import default

	return {"item": item, "user": frappe.session.user, "currency": currency, "time": default()}


def settle() -> None:
	"""Contract Work, made once; the workspace may change or replace it."""
	from onedesk.one_project.progress import LUMP_SUM

	if frappe.db.exists("Item", CONTRACT_ITEM) or not frappe.db.exists("UOM", LUMP_SUM):
		return
	group = "Services" if frappe.db.exists("Item Group", "Services") else None
	group = group or frappe.db.get_value("Item Group", {"is_group": 0}, "name", order_by="lft asc")
	if not group:
		return
	frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": CONTRACT_ITEM,
			"item_name": CONTRACT_ITEM,
			"item_group": group,
			"stock_uom": LUMP_SUM,
			"is_stock_item": 0,
			"is_sales_item": 1,
			"is_purchase_item": 1,
			"description": "Work under a fixed-price contract, billed as it gets done.",
		}
	).insert(ignore_permissions=True)
