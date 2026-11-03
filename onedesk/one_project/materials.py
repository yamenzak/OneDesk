"""Materials a project uses: bought into a store, issued to the project
from it, and what is left brought back. A stock item's cost is the project's
when it is issued, not when it is bought, even when the order was placed for
the project, so the same bars are never the project's twice; what comes back
is taken off again. Items that keep no stock are the project's cost when
billed, as before. README, Materials.
"""

from typing import Annotated

import frappe
from frappe import _
from frappe.query_builder.functions import Sum
from frappe.utils import flt
from hrms.overrides.employee_project import EmployeeProject

#: The Stock Entry Type a return to the store is made as.
RETURN = "Return to Store"


def into_store(projects: list[str]) -> float:
	"""What the projects' supplier bills came to on lines whose goods went
	into a store, received with the bill or on a receipt: those are the
	store's until they are issued."""
	if not projects:
		return 0.0
	found = frappe.db.sql(
		"""select sum(line.base_net_amount) from `tabPurchase Invoice Item` line
		where line.project in %(projects)s and line.docstatus = 1
		and exists (select 1 from `tabStock Ledger Entry` moved where moved.is_cancelled = 0
			and moved.voucher_detail_no in (line.name, ifnull(line.pr_detail, '')))""",
		{"projects": projects},
	)
	return flt(found[0][0]) if found else 0.0


def stocked(lines: list) -> set[str]:
	"""Of supplier bill lines ({name, pr_detail}), the ones whose goods went
	into a store."""
	keys = {key: one["name"] for one in lines for key in (one["name"], one.get("pr_detail")) if key}
	if not keys:
		return set()
	moved = frappe.get_all(
		"Stock Ledger Entry",
		filters={"voucher_detail_no": ["in", list(keys)], "is_cancelled": 0},
		pluck="voucher_detail_no",
	)
	return {keys[key] for key in moved}


def returned(projects: list[str]) -> float:
	"""What came back to the store from the projects."""
	if not projects:
		return 0.0
	line, entry = frappe.qb.DocType("Stock Entry Detail"), frappe.qb.DocType("Stock Entry")
	found = (
		frappe.qb.from_(line)
		.join(entry)
		.on(line.parent == entry.name)
		.select(Sum(line.amount))
		.where(line.project.isin(projects) & (line.docstatus == 1) & (entry.stock_entry_type == RETURN))
		.run()
	)
	return flt(found[0][0]) if found else 0.0


class OneProject(EmployeeProject):
	"""The project's material cost, less what came back to the store.
	ERPNext's purchase cost already leaves out what went into a store."""

	def set_consumed_material_cost(self):
		super().set_consumed_material_cost()
		self.total_consumed_material_cost = flt(self.total_consumed_material_cost) - returned([self.name])


def _return_type() -> str:
	if not frappe.db.exists("Stock Entry Type", RETURN):
		kind = frappe.get_doc({"doctype": "Stock Entry Type", "name": RETURN, "purpose": "Material Receipt"})
		kind.flags.ignore_permissions = True
		kind.insert()
	return RETURN


def _rate(item: str, project: str, warehouse: str) -> float:
	"""What a returned unit is worth: what the project was last charged for
	it, else what the store holds it at."""
	charged = frappe.get_all(
		"Stock Entry Detail",
		filters={"item_code": item, "project": project, "docstatus": 1, "s_warehouse": ["is", "set"], "t_warehouse": ["is", "not set"]},
		fields=["valuation_rate"],
		order_by="creation desc",
		limit=1,
	)
	if charged and flt(charged[0].valuation_rate):
		return flt(charged[0].valuation_rate)
	return flt(frappe.db.get_value("Bin", {"item_code": item, "warehouse": warehouse}, "valuation_rate"))


@frappe.whitelist(methods=["POST"])
def give_back(
	target: Annotated[str, "The store it comes back to."],
	lines: Annotated[list | str, "Each item, how many and in what unit: [{item, qty, uom}]."],
	project: Annotated[str, "The project it comes back from."],
	remarks: Annotated[str, "A note kept on the return."] | None = None,
) -> str:
	"""What a project didn't use, back on the store's shelf and off the
	project's cost, at what the project was charged for it."""
	from erpnext.stock.get_item_details import get_conversion_factor

	lines = frappe.parse_json(lines) if isinstance(lines, str) else lines
	wanted = [one for one in lines or [] if one.get("item") and flt(one.get("qty")) > 0]
	if not wanted:
		frappe.throw(_("Add an item and how many came back."))
	if not project:
		frappe.throw(_("Say which project it comes back from."))
	entry = frappe.new_doc("Stock Entry")
	entry.stock_entry_type = _return_type()
	entry.purpose = "Material Receipt"
	entry.company = frappe.db.get_value("Warehouse", target, "company")
	entry.to_warehouse, entry.project, entry.remarks = target, project, remarks or None
	for one in wanted:
		uom = one.get("uom") or frappe.db.get_value("Item", one["item"], "stock_uom")
		factor = flt(get_conversion_factor(one["item"], uom).get("conversion_factor")) or 1
		entry.append(
			"items",
			{
				"item_code": one["item"],
				"qty": flt(one["qty"]),
				"uom": uom,
				"conversion_factor": factor,
				"t_warehouse": target,
				"project": project,
				"basic_rate": _rate(one["item"], project, target) * factor,
			},
		)
	entry.insert()
	entry.submit()
	return entry.name
