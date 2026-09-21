// Nobody is asked which company, on a report either.
//
// `one/company.py` hides the Company field on every doctype that has one, but a
// report's filters are not doctype fields — they are a list declared in each
// report's own script, in another app. Seventeen of them in the OneHR rail alone
// asked which company, and each answer was the same one.
//
// So rather than seventeen forks of somebody else's report, the filter area is
// swept once after it is built: a Company link is filled from the site and
// hidden, and the "Include Company Descendants" checkbox beside it goes too,
// since it can only ever mean the same thing.
frappe.provide("onedesk.reports");

//: The checkbox has no other meaning on a single-company site, so it is named
//: rather than detected: nothing else is hidden by fieldname.
const ALSO = ["include_company_descendants"];

onedesk.reports.one_company = () => {
	const QueryReport = frappe.views && frappe.views.QueryReport;
	if (!QueryReport || QueryReport.prototype.__one_company) return;
	QueryReport.prototype.__one_company = true;

	const theirs = QueryReport.prototype.setup_filters;
	QueryReport.prototype.setup_filters = function () {
		theirs.call(this);
		(this.filters || []).forEach(hide_company);
	};
};

function hide_company(filter) {
	const df = filter.df || {};
	const company = df.fieldtype === "Link" && df.options === "Company";
	if (!company && !ALSO.includes(df.fieldname)) return;

	if (company && !filter.get_value()) {
		// `set_input` rather than `set_value`: the same one HRMS's own onload
		// uses, and it does not fire the onchange that would refetch mid-setup.
		filter.set_input(frappe.defaults.get_user_default("Company"));
	}
	df.hidden = 1;
	filter.$wrapper.addClass("one-gone");
}

// The heading is the record's name — "Employee Hours Utilization Based On
// Timesheet" under a rail row reading "Hours Utilization". The rail's own labels
// come down in the boot (see one/titles.py), so the page is called what the
// person clicked.
onedesk.reports.called_what_the_rail_called_it = () => {
	const QueryReport = frappe.views && frappe.views.QueryReport;
	if (!QueryReport || QueryReport.prototype.__one_titles) return;
	QueryReport.prototype.__one_titles = true;

	// The heading is the last breadcrumb, not `page_title` — `load_report` sets
	// that and nothing reads it. `set_breadcrumbs` runs late enough in the
	// serial chain to have the last word.
	const theirs = QueryReport.prototype.set_breadcrumbs;
	QueryReport.prototype.set_breadcrumbs = function () {
		theirs.call(this);
		const ours = ((frappe.boot.one_titles || {}).Report || {})[this.report_name];
		if (!ours) return;
		this.page_title = __(ours);
		frappe.breadcrumbs.add({
			type: "Custom",
			label: __(ours),
			route: `/app/query-report/${encodeURIComponent(this.report_name)}`,
		});
	};
};

// An employee column already says the name, so the column beside it does not.
//
// `one_hr/names.py` hides the mirror `Employee Name` field on the doctypes that
// carry one, and `show_title_field_in_link` makes every Employee link read the
// person's name. A report's columns are neither: they are a list built in
// Python in another app, and eleven of them in the OneHR rail put Employee and
// Employee Name side by side, reading "Samir Aoun | Samir Aoun".
//
// So the mirror column is dropped wherever the link it mirrors is present. Only
// then: a report that shows the name and not the link still shows the name.
onedesk.reports.one_name = () => {
	const QueryReport = frappe.views && frappe.views.QueryReport;
	if (!QueryReport || QueryReport.prototype.__one_name) return;
	QueryReport.prototype.__one_name = true;

	const theirs = QueryReport.prototype.prepare_columns;
	QueryReport.prototype.prepare_columns = function (columns) {
		const ready = theirs.call(this, columns);
		const linked = ready.some(
			(c) => c.fieldtype === "Link" && c.options === "Employee"
		);
		if (!linked) return ready;
		return ready.filter((c) => c.fieldname !== "employee_name");
	};
};

frappe.after_ajax(() => {
	onedesk.reports.one_company();
	onedesk.reports.one_name();
	onedesk.reports.called_what_the_rail_called_it();
});
