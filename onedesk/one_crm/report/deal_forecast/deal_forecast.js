// No company and no currency filter: one workspace is one company, and every
// amount is in its currency.
frappe.query_reports["Deal Forecast"] = {
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
			label: __("Deal Owner"),
			fieldtype: "Link",
			options: "User",
		},
	],
};
