"""What an encashed day is worth, and saying so before Submit rather than after."""

import frappe

FIELD = "leave_encashment_amount_per_day"


@frappe.whitelist()
def rate(employee: str, on: str) -> dict:
	"""The per-day rate this encashment would use, and where it came from.

	Same lookup order as `set_encashment_amount`: the assignment first, then the
	structure it names. Returns the structure either way, so the form can link to
	the place the rate is missing from.
	"""
	from hrms.payroll.doctype.salary_structure_assignment.salary_structure_assignment import (
		get_assigned_salary_structure,
	)

	frappe.has_permission("Leave Encashment", "create", throw=True)
	frappe.has_permission("Employee", "read", employee, throw=True)
	structure = get_assigned_salary_structure(employee, on)
	if not structure:
		return {"structure": None, "per_day": 0}

	per_day = frappe.db.get_value(
		"Salary Structure Assignment",
		{"employee": employee, "salary_structure": structure, "docstatus": 1, "from_date": ("<=", on)},
		FIELD,
		order_by="from_date desc",
	)
	if not per_day:
		per_day = frappe.db.get_value("Salary Structure", structure, FIELD)

	return {"structure": structure, "per_day": per_day or 0}
