// The filters, less the two that ask which company. Everything else is HRMS's
// own, because the questions it asks of a month are the right ones.
frappe.query_reports["Monthly Attendance"] = {
	filters: [
		{
			fieldname: "filter_based_on",
			label: __("Filter Based On"),
			fieldtype: "Select",
			options: ["Month", "Date Range"],
			default: "Month",
			reqd: 1,
			on_change: (report) => {
				const by_month =
					frappe.query_report.get_filter_value("filter_based_on") == "Month";
				required("month", by_month);
				required("year", by_month);
				required("start_date", !by_month);
				required("end_date", !by_month);
				report.refresh();
			},
		},
		{
			fieldname: "month",
			label: __("Month"),
			fieldtype: "Select",
			options: [
				{ value: 1, label: __("Jan") },
				{ value: 2, label: __("Feb") },
				{ value: 3, label: __("Mar") },
				{ value: 4, label: __("Apr") },
				{ value: 5, label: __("May") },
				{ value: 6, label: __("June") },
				{ value: 7, label: __("July") },
				{ value: 8, label: __("Aug") },
				{ value: 9, label: __("Sep") },
				{ value: 10, label: __("Oct") },
				{ value: 11, label: __("Nov") },
				{ value: 12, label: __("Dec") },
			],
			default: frappe.datetime.str_to_obj(frappe.datetime.get_today()).getMonth() + 1,
			depends_on: "eval:doc.filter_based_on == 'Month'",
		},
		{
			fieldname: "year",
			label: __("Year"),
			fieldtype: "Select",
			depends_on: "eval:doc.filter_based_on == 'Month'",
		},
		{
			fieldname: "start_date",
			label: __("Start Date"),
			fieldtype: "Date",
			depends_on: "eval:doc.filter_based_on == 'Date Range'",
			on_change: within_ninety,
		},
		{
			fieldname: "end_date",
			label: __("End Date"),
			fieldtype: "Date",
			depends_on: "eval:doc.filter_based_on == 'Date Range'",
			on_change: within_ninety,
		},
		{
			fieldname: "employee",
			label: __("Employee"),
			fieldtype: "Link",
			options: "Employee",
		},
		{
			fieldname: "status",
			label: __("Employment"),
			fieldtype: "Select",
			options: ["", "Active", "Inactive", "Suspended", "Left"],
			default: "Active",
		},
		{
			fieldname: "department",
			label: __("Department"),
			fieldtype: "Link",
			options: "Department",
		},
		{ fieldname: "branch", label: __("Branch"), fieldtype: "Link", options: "Branch" },
		{
			fieldname: "group_by",
			label: __("Group By"),
			fieldtype: "Select",
			options: ["", "Branch", "Grade", "Department", "Designation"],
		},
		{
			fieldname: "summarized_view",
			label: __("Totals Only"),
			fieldtype: "Check",
			default: 0,
		},
	],

	onload: () =>
		frappe
			.xcall(
				"hrms.hr.report.monthly_attendance_sheet.monthly_attendance_sheet.get_attendance_years",
			)
			.then((years) => {
				const filter = frappe.query_report.get_filter("year");
				filter.df.options = years;
				filter.df.default = years.split("\n")[0];
				filter.refresh();
				filter.set_input(filter.df.default);
			}),

	// The name is what a person reads and the id is what the link needs, so the
	// grid carries one column and this puts the other back into it.
	formatter(value, row, column, data, default_formatter) {
		if (column.fieldname === "employee_name" && data?.employee) {
			return `<a href="/desk/employee/${encodeURIComponent(data.employee)}">${frappe.utils.escape_html(value || data.employee)}</a>`;
		}

		value = default_formatter(value, row, column, data);
		if (frappe.query_report.get_filter_value("summarized_view")) return value;

		const colours = {
			P: "var(--green-500)",
			WFH: "var(--green-500)",
			"HD/P": "#914EE3",
			"HD/A": "var(--orange-500)",
			A: "var(--red-500)",
			L: "#3187D8",
		};
		const colour = colours[value] || (value ? "var(--gray-500)" : null);
		return colour ? `<span style="color:${colour}">${value}</span>` : value;
	},
};

function required(fieldname, yes) {
	const filter = frappe.query_report.get_filter(fieldname);
	filter.df.reqd = yes;
	filter.refresh();
}

function within_ninety(report) {
	const from = frappe.query_report.get_filter_value("start_date");
	const to = frappe.query_report.get_filter_value("end_date");
	if (!(from && to)) return;
	const days = frappe.datetime.get_day_diff(to, from);
	if (days > 90) {
		frappe.throw({
			message: __("A sheet covers at most {0} days.", [90]),
			title: __("Too Long"),
		});
	}
	report.refresh();
}
