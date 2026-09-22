"""What a payroll entry adds up to.

The account fix that used to live here moved to `one_hr/accounts.py` when the
same fault turned up a second time on the employee advance account.
"""

import frappe


@frappe.whitelist()
def run(name: str) -> dict:
	"""What a payroll entry adds up to, for the headline on it.

	The screen has the period and the account and a table of employees, and
	nowhere the two numbers anybody opens it for: how many people and how much.
	Counted off the slips rather than the `employees` table, because the table is
	who was *selected* and the slips are what was actually worked out.
	"""
	slips = frappe.get_all(
		"Salary Slip",
		filters={"payroll_entry": name, "docstatus": ("<", 2)},
		fields=["docstatus", "net_pay", "rounded_total", "currency"],
	)
	if not slips:
		return {"people": 0, "total": 0, "drafts": 0, "submitted": 0, "currency": None}

	return {
		"people": len(slips),
		"total": sum((slip.rounded_total or slip.net_pay or 0) for slip in slips),
		"drafts": sum(1 for slip in slips if slip.docstatus == 0),
		"submitted": sum(1 for slip in slips if slip.docstatus == 1),
		"currency": slips[0].currency,
	}
