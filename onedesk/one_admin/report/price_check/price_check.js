// Whether the price list makes sense (one_admin/plans.py, check). What is
// wrong comes first, in red; a close call in orange. The costs it measures
// against are One Admin Settings', which the menu opens.
frappe.query_reports["Price Check"] = {
	filters: [
		{
			fieldname: "include_disabled",
			label: __("Include Disabled"),
			fieldtype: "Check",
			default: 0,
		},
	],
	onload(report) {
		report.page.add_menu_item(__("Edit Costs"), () => frappe.set_route("Form", "One Admin Settings"));
	},
	formatter(value, row, column, data, default_formatter) {
		const shown = default_formatter(value, row, column, data);
		if (column.fieldname === "says" && data && data.indicator !== "green") {
			return `<span class="${data.indicator === "red" ? "text-danger" : "text-warning"}">${shown}</span>`;
		}
		return shown;
	},
};
