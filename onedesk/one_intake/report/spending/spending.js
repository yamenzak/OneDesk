// What was bought, read from the receipts and invoices. See spending.py.
frappe.query_reports["Spending"] = {
	filters: [
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date", reqd: 1, default: frappe.datetime.month_start() },
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date", reqd: 1, default: frappe.datetime.get_today() },
		{
			fieldname: "group_by",
			label: __("Group By"),
			fieldtype: "Select",
			options: ["Category", "Shop", "Person", "Month"].map((value) => ({ value, label: __(value) })),
			default: "Category",
		},
	],
};
