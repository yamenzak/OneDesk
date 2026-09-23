// This workspace's AI credits. The last thirty days unless asked otherwise:
// long enough to see a habit, short enough that a busy week stands out.
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
			options: ["Model", "Person", "Day"].join("\n"),
			default: "Model",
		},
	],
};
