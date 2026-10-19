"""The loose ends the import leaves on each project, for the project to say
until somebody settles them (rua/settle.py): money received and not
invoiced yet, payments left out as copies, and whether the client still
holds retention from invoices made outside the old app."""

import frappe
from frappe.utils import flt

from rua.importer.payments import PAYMENT, copies, family
from rua.importer.projects import PROJECT
from rua.settle import SETTLEMENT


def run(run_):
	open_ = {}

	def at(project):
		return open_.setdefault(project, {"advance": 0.0, "copies": [], "invoiced": False})

	for project, amount in frappe.db.sql(
		"""select coalesce(so.project, p.project), r.allocated_amount from `tabPayment Entry Reference` r
		join `tabPayment Entry` p on p.name = r.parent join `tabSales Order` so on so.name = r.reference_name
		where p.docstatus = 1 and p.payment_type = 'Receive' and r.reference_doctype = 'Sales Order'"""
	):
		if project:
			at(project)["advance"] += flt(amount)
	for project, amount in frappe.db.sql(
		"""select project, unallocated_amount from `tabPayment Entry`
		where docstatus = 1 and payment_type = 'Receive' and unallocated_amount > 0 and project is not null"""
	):
		at(project)["advance"] += flt(amount)
	payments = [one for one in run_.docs(PAYMENT) if one.get("status") == "Submitted"]
	by_name = {one["name"]: one for one in payments}
	for name in copies(payments, family(run_)):
		project = run_.made(PROJECT, by_name[name].get("project"), "Project")
		if project:
			at(project)["copies"].append(by_name[name])
	held = set(
		frappe.get_all("Sales Invoice", filters={"docstatus": 1, "one_retention": [">", 0]}, pluck="project")
	)
	for project in frappe.get_all(
		"Sales Invoice", filters={"docstatus": 1, "project": ["is", "set"]}, pluck="project"
	):
		if project not in held:
			at(project)["invoiced"] = True
	for project, said in open_.items():
		if frappe.db.exists(SETTLEMENT, project) or not frappe.db.exists("Project", project):
			continue
		advance = flt(said["advance"], 2)
		if advance <= 0.01 and not said["copies"] and not said["invoiced"]:
			continue
		frappe.get_doc(
			{
				"doctype": SETTLEMENT,
				"project": project,
				"advance": advance if advance > 0.01 else 0,
				"advance_state": "To Confirm" if advance > 0.01 else None,
				"retention_state": "To Ask" if said["invoiced"] else None,
				"copies": len(said["copies"]),
				"copies_amount": sum(flt(one.get("amount")) for one in said["copies"]),
				"copies_said": ", ".join(one["name"] for one in said["copies"]) or None,
			}
		).insert(ignore_permissions=True)
	waiting = frappe.db.count(SETTLEMENT, {"settled": 0})
	if waiting:
		run_.note(
			"To Check",
			None,
			None,
			f"{waiting} projects have something from the old app to settle; each says so",
		)
