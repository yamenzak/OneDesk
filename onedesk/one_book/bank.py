"""Where the Bank Reconciliation Tool opens (public/js/one_book/book_control.js)."""

import frappe


@frappe.whitelist()
@frappe.read_only()
def reconciling(company: str | None = None) -> dict | None:
	"""The company bank account with lines still to match, or its default
	one, and the date of the oldest line still to match."""
	from erpnext import get_default_company

	frappe.has_permission("Bank Transaction", "read", throw=True)
	company = company or get_default_company()
	waiting = frappe.get_list(
		"Bank Transaction",
		filters={"docstatus": 1, "status": "Unreconciled", "company": company},
		fields=["bank_account", {"MIN": "date", "as": "since"}, {"COUNT": "*", "as": "lines"}],
		group_by="bank_account",
		order_by="lines desc",
		limit_page_length=1,
	)
	if waiting:
		return {"bank_account": waiting[0].bank_account, "from_date": str(waiting[0].since)}
	account = next(
		iter(
			frappe.get_list(
				"Bank Account",
				filters={"company": company, "is_company_account": 1, "disabled": 0},
				pluck="name",
				order_by="is_default desc",
				limit=1,
			)
		),
		None,
	)
	return {"bank_account": account, "from_date": None} if account else None
