"""Who has what: an asset given to a person, taken back, and asked for when
they leave.

ERPNext keeps it on the asset (`custodian`) and changes it only through an
**Asset Movement**: a form with a purpose, a date and time, and a table of
assets with a source and target location and a from and to employee, where
which columns matter depends on the purpose. `give` and `take_back` are the
two movements a person makes, one step each from the asset's page (**Give
To…**, **Take Back**); the movement is still ERPNext's, so the asset's
history and its custodian are what ERPNext would have written.

A person's page counts what they hold (`held`, read by
one_hr/employee.overview). When they leave, `leaving` (Employee Separation
before_submit) adds a **Return** activity per asset to the separation's
checklist, which HRMS turns into tasks; HRMS's Full and Final Statement
already refuses to submit while an asset is unreturned, and this is how it
gets returned before then.
"""

import frappe
from frappe import _
from frappe.utils import now_datetime

#: Who is asked to take an asset back when its holder leaves.
KEEPER = "Stock Manager"


def _move(purpose: str, asset: str, **row) -> str:
	from erpnext import get_default_company

	movement = frappe.get_doc(
		{
			"doctype": "Asset Movement",
			"company": get_default_company(),
			"purpose": purpose,
			"transaction_date": now_datetime(),
			"assets": [{"asset": asset, **row}],
		}
	)
	movement.insert()
	movement.submit()
	return movement.name


@frappe.whitelist(methods=["POST"])
def give(asset: str, employee: str) -> str:
	"""The asset to `employee`, from whoever has it now."""
	holder = frappe.db.get_value("Asset", asset, "custodian")
	if holder == employee:
		frappe.throw(_("{0} already has it.").format(frappe.db.get_value("Employee", employee, "employee_name")))
	return _move("Issue", asset, to_employee=employee, from_employee=holder or None)


@frappe.whitelist(methods=["POST"])
def take_back(asset: str, location: str | None = None) -> str:
	"""The asset back from whoever has it, to `location` or where it was."""
	holder, where = frappe.db.get_value("Asset", asset, ["custodian", "location"])
	if not holder:
		frappe.throw(_("Nobody has it."))
	return _move("Receipt", asset, from_employee=holder, target_location=location or where)


def held(employee: str) -> list[dict]:
	return frappe.get_all(
		"Asset",
		filters={"custodian": employee, "docstatus": 1},
		fields=["name", "asset_name"],
		order_by="asset_name",
	)


def returns(assets: list[dict], have: set) -> list[dict]:
	"""A Return activity for each asset not already on the checklist. Pure."""
	return [
		{
			"activity_name": _("Return {0} ({1})").format(asset["asset_name"], asset["name"]),
			"role": KEEPER,
			"description": _("Take back {0} and record it with Take Back on the asset's page.").format(asset["name"]),
		}
		for asset in assets
		if not any(asset["name"] in line for line in have)
	]


def leaving(doc, method=None) -> None:
	"""Employee Separation before_submit: ask for the equipment back."""
	have = {row.activity_name or "" for row in doc.activities}
	for row in returns(held(doc.employee), have):
		doc.append("activities", row)
