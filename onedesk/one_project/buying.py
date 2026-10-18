"""What's being bought for a project, before and after the order: the
requests for material, the requests for prices sent to suppliers, the
quotations they sent back, the orders for goods, and the goods received.
"""

from typing import Annotated

import frappe
from frappe import _
from frappe.query_builder.functions import Sum
from frappe.utils import flt

from onedesk.one_inventory import heads
from onedesk.one_project import money, tree

PAPERS = {
	"Material Request": ("Material Request Item", "project", "transaction_date"),
	"Request for Quotation": ("Request for Quotation Item", "project_name", "transaction_date"),
	"Supplier Quotation": ("Supplier Quotation Item", "project", "transaction_date"),
	"Purchase Order": ("Purchase Order Item", "project", "transaction_date"),
	"Purchase Receipt": ("Purchase Receipt Item", "project", "posting_date"),
}

SHOWN = 20


@frappe.whitelist()
@frappe.read_only()
def papers(
	project: Annotated[str, "The project."],
	only: Annotated[bool | None, "Only the project's own work, not what is under it."] = None,
) -> dict:
	"""The tree's requests, supplier quotations and receipts, not cancelled,
	newest first, and which the reader may make."""
	frappe.has_permission("Project", "read", doc=project, throw=True)
	tree.narrow(project, only)
	projects = sorted(tree.scope(project))
	found = []
	for doctype, (child, field, day) in PAPERS.items():
		if not frappe.has_permission(doctype, "read"):
			continue
		line = frappe.qb.DocType(child)
		names = {
			one[0]: flt(one[1])
			for one in frappe.qb.from_(line)
			.select(line.parent, Sum(line.amount) if doctype != "Request for Quotation" else Sum(line.qty))
			.where(line[field].isin(projects) & (line.docstatus < 2))
			.groupby(line.parent)
			.run()
		}
		if doctype == "Purchase Order":
			goods = money.kinds(list(names))
			names = {name: amount for name, amount in names.items() if not goods[name]}
		if not names:
			continue
		fields = ["name", "status", "docstatus", day]
		if doctype in ("Supplier Quotation", "Purchase Receipt", "Purchase Order"):
			fields += ["supplier", "supplier_name", "currency"]
		if doctype == "Purchase Order":
			fields += ["per_received", "per_billed"]
		for one in frappe.get_list(
			doctype,
			filters={"name": ["in", list(names)]},
			fields=fields,
			order_by=f"{day} desc",
			limit_page_length=SHOWN,
		):
			tone = heads.stands(frappe.get_doc(doctype, one.name)) if doctype in heads.STANDS else None
			found.append(
				{
					"doctype": doctype,
					"name": one.name,
					"status": "Draft" if one.docstatus == 0 else one.status,
					"tone": tone,
					"date": str(one.get(day)) if one.get(day) else None,
					"party": one.get("supplier_name") or _suppliers(doctype, one.name),
					"supplier": one.get("supplier"),
					"amount": names[one.name] if doctype != "Request for Quotation" else None,
					"currency": one.get("currency"),
					"what": _items(child, one.name),
					"received": flt(one.per_received) if doctype == "Purchase Order" else None,
					"billed": flt(one.per_billed) if doctype == "Purchase Order" else None,
				}
			)
	found.sort(key=lambda one: one["date"] or "", reverse=True)
	logos = dict(
		frappe.get_all(
			"Supplier",
			filters={"name": ["in", list({one["supplier"] for one in found if one["supplier"]}) or [""]]},
			fields=["name", "image"],
			as_list=True,
		)
	)
	for one in found:
		one["party_image"] = logos.get(one.pop("supplier"))
	return {
		"papers": found,
		"can_request": bool(frappe.has_permission("Material Request", "create")),
		"can_ask": bool(frappe.has_permission("Request for Quotation", "create")),
	}


def _suppliers(doctype: str, name: str) -> str | None:
	"""Who a request for prices went to."""
	if doctype != "Request for Quotation":
		return None
	names = frappe.get_all(
		"Request for Quotation Supplier", filters={"parent": name}, pluck="supplier_name", order_by="idx asc"
	)
	return shown(names)


def _items(child: str, name: str) -> str | None:
	names = frappe.get_all(child, filters={"parent": name}, pluck="item_name", order_by="idx asc")
	return shown(names)


def shown(names: list) -> str | None:
	"""A list as one line: the first, and how many more. Pure."""
	names = [one for one in names if one]
	if not names:
		return None
	return names[0] if len(names) == 1 else _("{0} +{1}").format(names[0], len(names) - 1)
