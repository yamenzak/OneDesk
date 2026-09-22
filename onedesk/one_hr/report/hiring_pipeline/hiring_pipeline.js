// No company filter, and no staffing plan required: the period is the opening's
// posting date, and an opening nobody applied to is still a row.
frappe.query_reports["Hiring Pipeline"] = {
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
			default: frappe.datetime.year_end(),
		},
		{
			fieldname: "job_opening",
			label: __("Job Opening"),
			fieldtype: "Link",
			options: "Job Opening",
		},
		{
			fieldname: "designation",
			label: __("Designation"),
			fieldtype: "Link",
			options: "Designation",
		},
		{
			fieldname: "department",
			label: __("Department"),
			fieldtype: "Link",
			options: "Department",
		},
		{
			fieldname: "status",
			label: __("Opening Status"),
			fieldtype: "Select",
			options: ["", "Open", "Closed"],
		},
		{
			fieldname: "applicant_status",
			label: __("Applicant Status"),
			fieldtype: "Select",
			options: ["", "Open", "Replied", "Shortlisted", "Rejected", "Hold", "Accepted"],
		},
	],

	// Both names are titles, and the id behind each of them is an email address
	// or an HR-OPN number that nobody wants to read.
	formatter(value, row, column, data, default_formatter) {
		if (column.fieldname === "job_title" && data?.job_opening) {
			return `<a href="/desk/job-opening/${encodeURIComponent(data.job_opening)}">${frappe.utils.escape_html(value || data.job_opening)}</a>`;
		}
		if (column.fieldname === "applicant_name" && data?.job_applicant) {
			return `<a href="/desk/job-applicant/${encodeURIComponent(data.job_applicant)}">${frappe.utils.escape_html(value)}</a>`;
		}
		if (column.fieldname === "applicant_name" && !data?.job_applicant) {
			return `<span class="text-muted">${frappe.utils.escape_html(value || "")}</span>`;
		}
		return default_formatter(value, row, column, data);
	},
};
