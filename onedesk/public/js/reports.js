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

//: A Currency filter is swept only on a payroll or HR report, where the answer
//: is always what the company pays in. OneBook's are left alone: a single
//: company can still be owed money in somebody else's currency.
const PAID = ["HR", "Payroll", "One HR"];

onedesk.reports.one_company = () => {
	const QueryReport = frappe.views && frappe.views.QueryReport;
	if (!QueryReport || QueryReport.prototype.__one_company) return;
	QueryReport.prototype.__one_company = true;

	const theirs = QueryReport.prototype.setup_filters;
	QueryReport.prototype.setup_filters = function () {
		theirs.call(this);
		const paid = PAID.includes((this.report_doc || {}).module);
		(this.filters || []).forEach((filter) => hide_company(filter, paid));
	};
};

function hide_company(filter, paid) {
	const df = filter.df || {};
	const company = df.fieldtype === "Link" && df.options === "Company";
	const currency = paid && df.fieldtype === "Link" && df.options === "Currency";
	if (!company && !currency && !ALSO.includes(df.fieldname)) return;

	if (!filter.get_value()) {
		// `set_input` rather than `set_value`: the same one HRMS's own onload
		// uses, and it does not fire the onchange that would refetch mid-setup.
		if (company) filter.set_input(frappe.defaults.get_user_default("Company"));
		if (currency) filter.set_input(frappe.defaults.get_default("currency"));
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

// An employee column already says the name, so the column beside it does not —
// and no report column says which company.
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
		// The same company on every row, for the same reason the filter above it
		// is swept: there is only one.
		const kept = ready.filter((c) => c.fieldname !== "company");
		const linked = kept.some((c) => c.fieldtype === "Link" && c.options === "Employee");
		if (!linked) return kept;
		return kept.filter((c) => c.fieldname !== "employee_name");
	};
};

// A payroll register opens on the last payroll that was run.
//
// Salary Register ships `from_date` at today minus a month and `to_date` at
// today, and its query keeps a slip only when the whole slip sits inside the
// range. A month-ago-to-today range never contains a whole payroll month, so
// the report opens on "Nothing to show" however well payroll went — which is
// how it read here, with five submitted slips for August in the table and the
// range starting on the 22nd.
//
// Calendar months do not fix it either: payroll for August is read in
// September. So the dates come from the newest submitted slip — the register
// opens on the run somebody most recently made. It is a default and not a rule:
// a person who wants another range types one, and nothing resets it.
const MONTHLY = ["Salary Register"];

onedesk.reports.a_payroll_month = () => {
	const QueryReport = frappe.views && frappe.views.QueryReport;
	if (!QueryReport || QueryReport.prototype.__one_month) return;
	QueryReport.prototype.__one_month = true;

	const theirs = QueryReport.prototype.setup_filters;
	QueryReport.prototype.setup_filters = function () {
		theirs.call(this);
		if (!MONTHLY.includes(this.report_name)) return;
		const report = this;
		frappe.db
			.get_list("Salary Slip", {
				filters: { docstatus: 1 },
				fields: ["start_date", "end_date"],
				order_by: "end_date desc",
				limit: 1,
			})
			.then((found) => {
				if (!found.length) return;
				const run = { from_date: found[0].start_date, to_date: found[0].end_date };
				(report.filters || []).forEach((filter) => {
					const when = run[filter.df.fieldname];
					if (when) filter.set_input(when);
				});
				report.refresh();
			});
	};
};

// The same for a dashboard, at a different seam.
//
// A dashboard's heading is the last crumb too, but `Dashboard.set_breadcrumbs`
// passes only `{module, doctype, docname}` — and `set_dashboard_breadcrumb`
// reads a `label` its own caller never sends. So the crumb is labelled on its
// way through, and the browser tab with it. The Dashboard class is local to
// frappe's dashboard page and `frappe.dashboard` only exists once one has been
// drawn, so there is nothing else to wrap.
//
// The browser tab is left as it is. `Dashboard.show` calls `set_title` after
// the crumb, so anything written here is overwritten a line later, and a tab
// reading "Payroll Dashboard" beside a page reading "Payroll Overview" is not
// worth a second patch.
onedesk.reports.dashboards_too = () => {
	if (!frappe.breadcrumbs || frappe.breadcrumbs.__one_titles) return;
	frappe.breadcrumbs.__one_titles = true;

	const theirs = frappe.breadcrumbs.add;
	frappe.breadcrumbs.add = function (module, doctype, type) {
		const crumb = typeof module === "object" ? module : null;
		if (crumb && crumb.doctype === "Dashboard" && !crumb.label) {
			const ours = ((frappe.boot.one_titles || {}).Dashboard || {})[crumb.docname];
			if (ours) crumb.label = ours;
		}
		return theirs.call(this, module, doctype, type);
	};
};

frappe.after_ajax(() => {
	onedesk.reports.one_company();
	onedesk.reports.one_name();
	onedesk.reports.a_payroll_month();
	onedesk.reports.called_what_the_rail_called_it();
	onedesk.reports.dashboards_too();
});
