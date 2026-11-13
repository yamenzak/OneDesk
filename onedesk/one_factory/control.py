"""OneFactory's Workshop settings (public/js/one_factory/factory_control.js):
the account workshop time is costed to and the warehouses a new work order
takes, each the reader's default company's own fields on Company."""

import frappe
from frappe import _

from onedesk.one.company import reader_company

FIELDS = ("default_operating_cost_account", "default_wip_warehouse", "default_fg_warehouse")


def _company() -> str:
	company = reader_company()
	if not company:
		frappe.throw(_("Add a company first."))
	return company


@frappe.whitelist()
def workshop() -> dict:
	"""The company's three, and what One would use where one is empty."""
	company = _company()
	frappe.has_permission("Company", "read", doc=company, throw=True)
	said = frappe.db.get_value("Company", company, FIELDS, as_dict=True)
	return {
		"company": company,
		"may": bool(frappe.has_permission("Company", "write", doc=company)),
		**said,
		"suggested": suggested(company),
	}


def suggested(company: str) -> dict:
	"""The account ERPNext keeps for costs that go into what stock is worth,
	and the company's Work In Progress and Finished Goods warehouses."""
	return {
		"default_operating_cost_account": frappe.db.get_value(
			"Account", {"company": company, "account_type": "Expenses Included In Valuation", "is_group": 0, "disabled": 0}
		),
		"default_wip_warehouse": frappe.db.get_value("Warehouse", {"company": company, "warehouse_name": "Work In Progress", "is_group": 0}),
		"default_fg_warehouse": frappe.db.get_value("Warehouse", {"company": company, "warehouse_name": "Finished Goods", "is_group": 0}),
	}


@frappe.whitelist(methods=["POST"])
def save_workshop(
	default_operating_cost_account: str | None = None,
	default_wip_warehouse: str | None = None,
	default_fg_warehouse: str | None = None,
) -> dict:
	"""The three saved on the company, as its own form would save them."""
	company = frappe.get_doc("Company", _company())
	company.check_permission("write")
	company.update(
		{
			"default_operating_cost_account": default_operating_cost_account or None,
			"default_wip_warehouse": default_wip_warehouse or None,
			"default_fg_warehouse": default_fg_warehouse or None,
		}
	)
	company.save()
	return workshop()


def costed() -> bool:
	"""Whether workshop time has an account to go to."""
	company = reader_company()
	return bool(company and frappe.db.get_value("Company", company, "default_operating_cost_account"))


def placed() -> bool:
	"""Whether a new work order knows where to work and where to put what it makes."""
	company = reader_company()
	said = company and frappe.db.get_value("Company", company, ["default_wip_warehouse", "default_fg_warehouse"])
	return bool(said and all(said))
