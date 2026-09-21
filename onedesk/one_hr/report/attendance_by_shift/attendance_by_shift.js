// No company filter, and no "Include Shift Attendance Without Checkins": every
// day in the period is a row, so there is nothing left to opt back into.
frappe.query_reports["Attendance by Shift"] = {
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
		{ fieldname: "shift", label: __("Shift"), fieldtype: "Link", options: "Shift Type" },
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: ["", "Present", "Absent", "Half Day", "On Leave", "Work From Home"],
		},
		{
			fieldname: "department",
			label: __("Department"),
			fieldtype: "Link",
			options: "Department",
		},
		{ fieldname: "late_entry", label: __("Late Only"), fieldtype: "Check" },
		{ fieldname: "early_exit", label: __("Left Early Only"), fieldtype: "Check" },
		{
			fieldname: "consider_grace_period",
			label: __("Allow the Grace Period"),
			fieldtype: "Check",
			default: 1,
		},
	],

	// The name is what a person reads and the id is what the link needs.
	formatter(value, row, column, data, default_formatter) {
		if (column.fieldname === "employee_name" && data?.employee) {
			return `<a href="/desk/employee/${encodeURIComponent(data.employee)}">${frappe.utils.escape_html(value || data.employee)}</a>`;
		}
		return default_formatter(value, row, column, data);
	},
};
