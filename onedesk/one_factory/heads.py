"""What a work order's, a bill of materials', a job card's and a
subcontracting order's form say above their fields: the heads, the measures
they place. See one/head.py.
"""

from urllib.parse import quote

import frappe
from frappe import _, _lt
from frappe.utils import flt, fmt_money, formatdate

from onedesk.one import stages

SUBMITTED = [["docstatus", "=", 1]]


def _money(value, company: str | None) -> str:
	"""An amount in the company's own currency."""
	from erpnext import get_company_currency

	return fmt_money(flt(value), currency=get_company_currency(company) if company else None)


def _of(made, wanted, unit) -> dict:
	"""So many of so many, with a meter."""
	said = _("{0} of {1}").format(fmt_money(flt(made), precision=0), fmt_money(flt(wanted), precision=0))
	return {"value": f"{said} {_(unit or '')}".strip(), "meter": {"value": flt(made), "of": flt(wanted)}}


def work_progress(doc):
	"""Planned, materials sent, the steps, made."""
	if doc.docstatus != 1:
		return None
	made = flt(doc.produced_qty) >= flt(doc.qty)
	late = not made and bool(stages.overdue(doc.expected_delivery_date))
	sent = flt(doc.material_transferred_for_manufacturing)
	unit = _(doc.stock_uom or "")
	steps = len(doc.operations)
	finished = sum(1 for row in doc.operations if row.status == "Completed")
	return stages.track(
		stages.step(_("Planned"), "done", formatdate(doc.planned_start_date)),
		not doc.skip_transfer
		and stages.step(
			_("Material Transferred"),
			stages.at(sent >= flt(doc.qty), True, late and not sent),
			_("All on the floor") if sent >= flt(doc.qty) else stages.share(100 * sent / flt(doc.qty)) if flt(doc.qty) else "",
		),
		steps
		and stages.step(_("Operations"), stages.at(finished >= steps, sent or doc.skip_transfer), _("{0} of {1}").format(finished, steps)),
		stages.step(
			_("Manufactured"),
			stages.at(made, flt(doc.produced_qty) or (not steps and (sent or doc.skip_transfer)), late),
			_("{0} of {1} {2}").format(fmt_money(flt(doc.produced_qty), precision=0), fmt_money(flt(doc.qty), precision=0), unit).strip(),
		),
		stopped=doc.status in ("Stopped", "Closed"),
	)


def work_said(doc):
	what = doc.item_name or doc.production_item
	if said := stages.draft(doc, _("A draft. Submit it to plan making {0}.").format(what)):
		return said
	if doc.status in ("Stopped", "Closed"):
		return {"text": _("{0}; nothing more will be made on it.").format(_(doc.status)), "colour": "gray"}
	if doc.status == "Completed":
		return {"text": _("All made."), "colour": "green"}
	days = stages.overdue(doc.expected_delivery_date)
	if days:
		return {"text": _("Not finished, and it was wanted {0} ago.").format(stages.days(days)), "colour": "red"}
	if not doc.skip_transfer and not flt(doc.material_transferred_for_manufacturing):
		return {"text": _("Send the materials to the floor to start."), "colour": "orange"}
	if doc.expected_delivery_date:
		return {"text": _("Being made; wanted by {0}.").format(formatdate(doc.expected_delivery_date)), "colour": "blue"}
	return {"text": _("Being made."), "colour": "blue"}


def sub_progress(doc):
	"""Ordered, materials sent, back."""
	if doc.docstatus != 1:
		return None
	wanted = sum(flt(row.required_qty) for row in doc.supplied_items)
	sent = sum(flt(row.supplied_qty) for row in doc.supplied_items)
	back = flt(doc.per_received) >= 100
	late = not back and bool(stages.overdue(doc.schedule_date))
	return stages.track(
		stages.step(_("Ordered"), "done", formatdate(doc.transaction_date)),
		wanted
		and stages.step(_("Material Transferred"), stages.at(sent >= wanted, True, late and not sent), _("All") if sent >= wanted else stages.share(100 * sent / wanted)),
		stages.step(_("Received"), stages.at(back, sent or not wanted, late and bool(sent)), _("All") if back else stages.share(doc.per_received)),
		stopped=doc.status == "Closed",
	)


def sub_said(doc):
	supplier = doc.supplier_name or doc.supplier
	if said := stages.draft(doc, _("A draft. Submit it to send work to {0}.").format(supplier)):
		return said
	if doc.status == "Closed":
		return {"text": _("Closed; nothing more is expected on it."), "colour": "gray"}
	if flt(doc.per_received) >= 100:
		return {"text": _("All back from {0}.").format(supplier), "colour": "green"}
	days = stages.overdue(doc.schedule_date)
	if doc.status in ("Open", "Partial Material Transferred"):
		return {"text": _("Send the materials to {0} to start.").format(supplier), "colour": "red" if days else "orange"}
	if days:
		return {"text": _("With {0}, and it was wanted back {1} ago.").format(supplier, stages.days(days)), "colour": "red"}
	if doc.schedule_date:
		return {"text": _("With {0}; wanted back by {1}.").format(supplier, formatdate(doc.schedule_date)), "colour": "blue"}
	return {"text": _("With {0}.").format(supplier), "colour": "blue"}


def bom_said(doc):
	what = doc.item_name or doc.item
	if said := stages.draft(doc, _("A draft. Submit it to make {0} from it.").format(what)):
		return said
	if not doc.is_active:
		return {"text": _("Not in use; new work orders cannot pick it."), "colour": "gray"}
	if doc.is_default:
		return {"text": _("New work orders for {0} use this one.").format(what), "colour": "green"}
	default = frappe.db.get_value("BOM", {"item": doc.item, "is_default": 1, "docstatus": 1}, "name")
	if default:
		return {"text": _("In use, but new work orders for {0} pick {1}.").format(what, default), "colour": "orange"}
	return {"text": _("In use, and no BOM for {0} is the default.").format(what), "colour": "orange"}


def work_for(doc):
	"""Who it is made for: the customer's order, or whoever asked for it."""
	if doc.sales_order:
		customer = frappe.db.get_value("Sales Order", doc.sales_order, "customer_name")
		return {"value": customer or doc.sales_order, "route": f"/desk/sales-order/{quote(doc.sales_order)}"}
	if doc.material_request:
		owner = frappe.db.get_value("Material Request", doc.material_request, "owner")
		return {"value": frappe.utils.get_fullname(owner), "route": f"/desk/material-request/{quote(doc.material_request)}"}
	return None


def bom_cost(doc):
	"""What one costs to make, by the materials and the work it takes, in
	its company's currency, for whoever may see what making costs
	(costs.py)."""
	from onedesk.one_factory import costs

	if not flt(doc.quantity) or not costs.seen():
		return None
	return _money(flt(doc.base_total_cost) / flt(doc.quantity), doc.company)


def bom_orders(doc):
	made = frappe.db.count("Work Order", {"bom_no": doc.name, "docstatus": 1})
	return {
		"value": str(made),
		"tone": None if made else "quiet",
		"route": f"/desk/work-order?bom_no={quote(doc.name)}" if made else None,
	}


def bom_steps(doc):
	if not doc.with_operations or not doc.operations:
		return None
	return " · ".join(dict.fromkeys(_(row.operation) for row in doc.operations))


def card_order(doc):
	if not doc.work_order:
		return None
	made = frappe.db.get_value("Work Order", doc.work_order, "item_name")
	return {"value": made or doc.work_order, "route": f"/desk/work-order/{quote(doc.work_order)}"}


def card_done(doc):
	return _of(doc.total_completed_qty, doc.for_quantity, frappe.db.get_value("Work Order", doc.work_order, "stock_uom"))


def card_time(doc):
	minutes = flt(doc.total_time_in_mins)
	if not minutes:
		return {"value": _("None yet"), "tone": "quiet"}
	return _("{0} h").format(frappe.format(minutes / 60, {"fieldtype": "Float", "precision": 1}))


def card_by(doc):
	names = list(dict.fromkeys(row.employee for row in doc.time_logs if row.employee))
	if not names:
		return None
	if len(names) > 1:
		return _("{0} people").format(len(names))
	return frappe.db.get_value("Employee", names[0], "employee_name") or names[0]


def sub_order(doc):
	orders = list(dict.fromkeys(row.subcontracting_order for row in doc.items if row.subcontracting_order))
	if len(orders) != 1:
		return None
	return {"value": orders[0], "route": f"/desk/subcontracting-order/{quote(orders[0])}"}


MEASURES = {
	"work.progress": work_progress,
	"work.said": work_said,
	"sub.progress": sub_progress,
	"sub.said": sub_said,
	"bom.said": bom_said,
	"work.for": work_for,
	"bom.cost": bom_cost,
	"bom.orders": bom_orders,
	"bom.steps": bom_steps,
	"card.order": card_order,
	"card.done": card_done,
	"card.time": card_time,
	"card.by": card_by,
	"sub.order": sub_order,
}


HEADS = [
	{
		"doctype": "Work Order",
		"sentences": [{"measure": "work.said"}],
		"band": [
			{"label": _lt("Progress"), "source": "Measure", "measure": "work.progress"},
			{"label": _lt("Project"), "source": "Measure", "measure": "project.of"},
			{"label": _lt("Sales Order or Material Request"), "source": "Measure", "measure": "work.for"},
		],
	},
	{
		"doctype": "BOM",
		"sentences": [{"measure": "bom.said"}],
		"band": [
			{"label": _lt("Cost per Unit"), "source": "Measure", "measure": "bom.cost"},
			{"label": _lt("Operations"), "source": "Measure", "measure": "bom.steps"},
			{"label": _lt("Work Order"), "source": "Measure", "measure": "bom.orders", "shown_when": SUBMITTED},
		],
	},
	{
		"doctype": "Job Card",
		"band": [
			{"label": _lt("Work Order"), "source": "Measure", "measure": "card.order"},
			{"label": _lt("Workstation"), "source": "Field", "field": "workstation"},
			{"label": _lt("Completed"), "source": "Measure", "measure": "card.done"},
			{"label": _lt("Time Taken"), "source": "Measure", "measure": "card.time"},
			{"label": _lt("Employee"), "source": "Measure", "measure": "card.by"},
		],
	},
	{
		"doctype": "Subcontracting Order",
		"sentences": [{"measure": "sub.said"}],
		"band": [
			{"label": _lt("Progress"), "source": "Measure", "measure": "sub.progress"},
			{"label": _lt("Project"), "source": "Measure", "measure": "project.of"},
			{"label": _lt("Total"), "source": "Field", "field": "total"},
		],
	},
	{
		"doctype": "Subcontracting Receipt",
		"band": [
			{"label": _lt("Project"), "source": "Measure", "measure": "project.of"},
			{"label": _lt("Supplier"), "source": "Field", "field": "supplier_name"},
			{"label": _lt("Subcontracting Order"), "source": "Measure", "measure": "sub.order"},
			{"label": _lt("Total"), "source": "Field", "field": "total"},
		],
	},
]
