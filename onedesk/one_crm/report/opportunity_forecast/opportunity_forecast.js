frappe.query_reports["Opportunity Forecast"] = {
	filters: [
		{
			fieldname: "from_month",
			label: __("From"),
			fieldtype: "Date",
			default: frappe.datetime.month_start(),
		},
		{
			fieldname: "months",
			label: __("Months"),
			fieldtype: "Int",
			default: 6,
		},
		{
			fieldname: "owner",
			label: __("Opportunity Owner"),
			fieldtype: "Link",
			options: "User",
		},
	],
};
