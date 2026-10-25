frappe.query_reports["AI Usage"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_start(),
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
			options: ["Workspace", "Model", "Action", "Workspace and Model", "Workspace and Action"].join("\n"),
			default: "Workspace",
		},
		{
			fieldname: "tenant",
			label: __("Workspace"),
			fieldtype: "Link",
			options: "Tenant",
		}
		{
			fieldname: "model",
			label: __("Model"),
			fieldtype: "Data",
		},
	],
	formatter(value, row, column, data, default_formatter) {
		const shown = default_formatter(value, row, column, data);
		return data && data.bold ? `<b>${shown}</b>` : shown;
	},
};
