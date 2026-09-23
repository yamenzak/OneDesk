frappe.query_reports["Won and Lost"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.year_start(),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "group_by",
			label: __("Group By"),
			fieldtype: "Select",
			options: [
				{ value: "Month", label: __("Month") },
				{ value: "Deal Owner", label: __("Deal Owner") },
				{ value: "Source", label: __("Source") },
				{ value: "Lost Reason", label: __("Lost Reason") },
			],
			default: "Month",
		},
	],
};
