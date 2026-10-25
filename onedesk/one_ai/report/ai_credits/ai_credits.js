frappe.query_reports["AI Credits"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_days(frappe.datetime.get_today(), -29),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "by",
			label: __("By"),
			fieldtype: "Select",
			options: ["Job", "Person", "Day"].join("\n"),
			default: "Job",
		},
	],
};
