"""The demo's history on the day each thing happened. The demo is built in
one sitting and back-dates its documents (`base.dated`), but frappe stamps
each with the moment it was saved, so a timeline would show April's invoice
as made yesterday. Each document dated in the past is moved back to its own
date, with its versions and child rows, the time of day kept."""

import frappe

#: What says when each happened, by doctype.
DATES = {
	"Quotation": "transaction_date",
	"Sales Order": "transaction_date",
	"Delivery Note": "posting_date",
	"Sales Invoice": "posting_date",
	"Material Request": "transaction_date",
	"Request for Quotation": "transaction_date",
	"Supplier Quotation": "transaction_date",
	"Purchase Order": "transaction_date",
	"Purchase Receipt": "posting_date",
	"Purchase Invoice": "posting_date",
	"Payment Entry": "posting_date",
	"Journal Entry": "posting_date",
	"Stock Entry": "posting_date",
	"Expense Claim": "posting_date",
	"Project": "expected_start_date",
	"Project Update": "date",
	"Task": "exp_start_date",
	"Timesheet": "start_date",
}


def settle() -> int:
	"""Move every document saved after its own date back to that date. Run
	again, it moves nothing. Returns how many moved."""
	moved = 0
	for doctype, field in DATES.items():
		rows = frappe.db.sql(
			f"""select name, timestampdiff(second, creation, timestamp({field}, time(creation))) as shift
			from `tab{doctype}` where {field} is not null and date(creation) > {field}""",
			as_dict=True,
		)
		children = [one.options for one in frappe.get_meta(doctype).get_table_fields()]
		for row in rows:
			_shift(doctype, row.name, row.shift)
			for child in children:
				frappe.db.sql(
					f"""update `tab{child}` set creation = timestampadd(second, %(s)s, creation),
					modified = timestampadd(second, %(s)s, modified) where parent = %(p)s and parenttype = %(t)s""",
					{"s": row.shift, "p": row.name, "t": doctype},
				)
			frappe.db.sql(
				"""update `tabVersion` set creation = timestampadd(second, %(s)s, creation),
				modified = timestampadd(second, %(s)s, modified) where ref_doctype = %(t)s and docname = %(p)s""",
				{"s": row.shift, "p": row.name, "t": doctype},
			)
		moved += len(rows)
	return moved


def _shift(doctype: str, name: str, seconds: int) -> None:
	frappe.db.sql(
		f"""update `tab{doctype}` set creation = timestampadd(second, %(s)s, creation),
		modified = timestampadd(second, %(s)s, modified) where name = %(n)s""",
		{"s": seconds, "n": name},
	)
