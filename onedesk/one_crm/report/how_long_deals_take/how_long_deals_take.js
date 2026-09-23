frappe.query_reports["How Long Deals Take"] = {
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
			label: __("Deal Owner"),
			fieldtype: "Link",
			options: "User",
		},
	],
	formatter(value, row, column, data, default_formatter) {
		const shown = default_formatter(value, row, column, data);
		if (column.fieldname === "stuck" && value) return `<span style="color: var(--orange-600)">${shown}</span>`;
		return shown;
	},
};
