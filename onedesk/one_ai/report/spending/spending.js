frappe.query_reports["Spending"] = {
	filters: [
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date", reqd: 1, default: frappe.datetime.month_start() },
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date", reqd: 1, default: frappe.datetime.get_today() },
		{
			fieldname: "group_by",
			label: __("Group By"),
			fieldtype: "Select",
			options: ["Category", "Shop", "Person", "Month"].map((value) => ({ value, label: __(value) })),
			default: "Category",
		},
	],
	onload(report) {
		report.page.add_inner_button(__("Documents for the Tax Year"), () => {
			const year = (report.get_filter_value("to_date") || frappe.datetime.get_today()).slice(0, 4);
			window.open(`/api/method/onedesk.one_ai.reading.bundle.year?year=${encodeURIComponent(year)}`);
		});
	},
};
