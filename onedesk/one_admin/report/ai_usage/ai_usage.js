// Who spends on AI, and on what. A month at a time unless asked otherwise,
// because a month is what a workspace is billed in.
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
			options: ["Workspace", "Model", "Workspace and Model"].join("\n"),
			default: "Workspace",
		},
		{
			fieldname: "tenant",
			label: __("Workspace"),
			fieldtype: "Link",
			options: "Tenant",
		},
		{
			fieldname: "model",
			label: __("Model"),
			fieldtype: "Link",
			options: "AI Model",
		},
	],
};
