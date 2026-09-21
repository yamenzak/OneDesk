// No company filter: one workspace is one company.
frappe.query_reports["Hours Utilization"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_start(),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_end(),
			reqd: 1,
		},
		{ fieldname: "employee", label: __("Employee"), fieldtype: "Link", options: "Employee" },
		{
			fieldname: "department",
			label: __("Department"),
			fieldtype: "Link",
			options: "Department",
		},
		{ fieldname: "project", label: __("Project"), fieldtype: "Link", options: "Project" },
	],

	// The name is what a person reads and the id is what the link needs.
	formatter(value, row, column, data, default_formatter) {
		if (column.fieldname === "employee_name" && data?.employee) {
			return `<a href="/desk/employee/${encodeURIComponent(data.employee)}">${frappe.utils.escape_html(value || data.employee)}</a>`;
		}
		return default_formatter(value, row, column, data);
	},
};
