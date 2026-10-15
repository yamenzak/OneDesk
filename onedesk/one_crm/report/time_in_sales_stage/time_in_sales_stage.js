frappe.query_reports["Time in Sales Stage"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_days(frappe.datetime.get_today(), -365),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "owner",
			label: __("Opportunity Owner"),
			fieldtype: "Link",
			options: "User",
		},
	],
	formatter(value, row, column, data, default_formatter) {
		const shown = default_formatter(value, row, column, data);
		if (column.fieldname === "stuck" && value) return `<span style="color: var(--ink-amber-6)">${shown}</span>`;
		return shown;
	},
};
