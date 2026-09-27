// Whether the price list makes sense (one_admin/plans.py, check).
frappe.query_reports["Price Check"] = {
	filters: [],
	formatter(value, row, column, data, default_formatter) {
		const shown = default_formatter(value, row, column, data);
		if (column.fieldname === "says" && data && data.indicator !== "green") {
			return `<span class="${data.indicator === "red" ? "text-danger" : "text-warning"}">${shown}</span>`;
		}
		return shown;
	},
};
