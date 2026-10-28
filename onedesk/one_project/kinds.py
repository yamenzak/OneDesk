"""A project's kind: how it's paid for, which decides what it asks for when it
is made and what its page shows (one_project/AGENTS.md).
"""

from typing import Annotated

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate, nowdate

from onedesk.one_book.currency import bill_in, billed_in
from onedesk.one_project import library, terms

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


def held(doc, method=None) -> None:
	"""Project validate, after a sub-project takes its parent's customer: what
	the kind needs, and nothing it doesn't, however the kind is set (the New
	Project dialog, the form, a bulk edit, an import). A project that bills
	has a customer and an internal one has none; a monthly fee and hours are
	a retainer's, and a markup is time and materials'."""
	kind = doc.get("one_kind")
	if kind == INTERNAL:
		doc.customer = None
		doc.one_payment_terms = None
		doc.one_terms = None
	elif kind in KINDS and not doc.get("customer"):
		frappe.throw(_("Pick the customer {0} bills.").format(doc.project_name))
	if kind != RETAINER:
		doc.one_monthly_fee = 0
		doc.one_monthly_hours = 0
	if kind != TIME:
		doc.one_markup = 0


SETTLED = ("customer", "one_kind")


def in_use(name: str | None) -> bool:
	"""Whether the project has a sales order or invoice that isn't cancelled."""
	return bool(
		name
		and any(
			frappe.db.exists(doctype, {"project": name, "docstatus": ["<", 2]})
			for doctype in ("Sales Order", "Sales Invoice")
		)
	)


def settled(doc, method=None) -> None:
	"""Project validate: its customer and kind stay as they are once it has
	orders or invoices, which already bill that customer that way."""
	before = doc.get_doc_before_save()
	if not before:
		return
	moved = [field for field in SETTLED if (before.get(field) or None) != (doc.get(field) or None)]
	if moved and in_use(doc.name):
		frappe.throw(_("{0} has orders or invoices, so its customer and kind stay as they are.").format(doc.project_name))


@frappe.whitelist()
def settled_fields(project: Annotated[str, "The project."]) -> list[str]:
	"""The fields the Edit About dialog shows as fixed: the customer and kind
	once the project has orders or invoices."""
	frappe.has_permission("Project", "read", doc=project, throw=True)
	return list(SETTLED) if in_use(project) else []


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

	template = values.template or (values.library and library.copy(values.library)) or None
	agreed = terms.defaults(values.client if kind != INTERNAL else None, template)
	for key in ("payment_terms", "terms"):
		values[key] = values.get(key) or (None if values.parent else agreed[key])
	if values.retention is None and kind == FIXED:
		values.retention, values.retention_handover = agreed["retention"], agreed["retention_handover"]
	project = frappe.new_doc("Project")
	project.update(
		{
			"project_name": (values.title or "").strip(),
			"one_kind": kind,
			"customer": values.client if kind != INTERNAL else None,
			"expected_start_date": values.starts,
			"expected_end_date": values.ends,
			"one_manager": values.manager or frappe.session.user,
			"project_template": template,
			"one_payment_terms": values.payment_terms if kind != INTERNAL else None,
			"one_terms": values.terms if kind != INTERNAL else None,
			"estimated_costing": flt(values.budget) if kind in (TIME, INTERNAL) else 0,
			"one_monthly_fee": flt(values.monthly_fee) if kind == RETAINER else 0,
			"one_monthly_hours": flt(values.monthly_hours) if kind == RETAINER else 0,
			"one_markup": flt(values.markup) if kind == TIME else 0,
			"one_time": values.time,
			"one_site": values.site,
			"one_retention": flt(values.retention) if kind == FIXED else 0,
			"one_retention_due": values.retention_due if kind == FIXED and flt(values.retention) else None,
			"one_retention_handover": flt(values.retention_handover) if kind == FIXED and flt(values.retention) else 0,
		}
	)
	if values.parent:
		project.one_parent = values.parent
	project.flags.one_terms_given = True
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
	terms.give(order, *terms.of(project.name)[:2])
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
	payment_terms: Annotated[str | None, "When its invoices are due, a Payment Terms Template."] = None,
	conditions: Annotated[str | None, "The Terms and Conditions printed on it."] = None,
) -> str:
	"""A Fixed Price project's contract, made after the project: the same
	submitted Sales Order the New Project dialog makes, with the project's
	terms, which `payment_terms` and `conditions` change for both. Returns
	its name."""
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
	changed = {
		field: value
		for field, value in (("one_payment_terms", payment_terms), ("one_terms", conditions))
		if value and value != doc.get(field)
	}
	if changed:
		doc.update(changed)
		doc.save()
	order = _contract(doc, values, flt(contract))
	doc.db_set("sales_order", order)
	return order


CONTRACT_ITEM = "Contract Work"


@frappe.whitelist()
@frappe.read_only()
def defaults(
	customer: Annotated[str | None, "The customer, for their currency and terms."] = None,
	template: Annotated[str | None, "The Project Template it starts from, for its terms."] = None,
) -> dict:
	"""What the New Project and Add Contract dialogs start with: the item the
	last project's contract was billed as, or Contract Work, the currency the
	customer is billed in, how the workspace counts time, and the payment terms,
	terms and conditions and retention to agree (terms.py)."""
	billable = frappe.get_all("Item", filters={"is_sales_item": 1, "disabled": 0, "is_stock_item": 0}, pluck="name")
	found = frappe.get_all(
		"Sales Order Item",
		filters={"docstatus": 1, "project": ["is", "set"], "item_code": ["in", billable or [""]]},
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

	agreed = terms.defaults(
		customer if customer and frappe.has_permission("Customer", "read", doc=customer) else None,
		template if template and frappe.has_permission("Project Template", "read", doc=template) else None,
	)
	return {"item": item, "user": frappe.session.user, "currency": currency, "time": default(), **agreed}


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
