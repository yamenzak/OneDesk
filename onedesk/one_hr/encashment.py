"""What an encashed day is worth, and saying so before Submit rather than after.

HRMS works the amount out from `leave_encashment_amount_per_day`, a field on the
Salary Structure Assignment or, failing that, on the Salary Structure. Nothing
fills it and nothing asks for it, so on a workspace that has not found it every
encashment reads **0.00** and `before_submit` answers *"You can only submit
Leave Encashment for a valid encashment amount"* — after the form has been
filled in, and without saying which field is missing or where it lives.

So the form says it first, on the record, with a link to the structure it would
be set on. Deriving a rate instead was considered and rejected: a day's pay is
`base / working days` or `base / 30` or the basic component alone depending on
the contract and the country, and a product that guesses pays somebody the wrong
amount without being asked.
"""

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
