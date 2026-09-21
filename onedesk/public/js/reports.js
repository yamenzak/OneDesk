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

frappe.after_ajax(() => onedesk.reports.one_company());
