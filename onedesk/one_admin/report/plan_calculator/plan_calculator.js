// What a workspace needing this much would pay, every way it could.
frappe.query_reports["Plan Calculator"] = {
	filters: [
		{ fieldname: "seats", label: __("Seats"), fieldtype: "Int", default: 10 },
		{ fieldname: "storage_gb", label: __("Storage (GB)"), fieldtype: "Int", default: 50 },
		{ fieldname: "database_gb", label: __("Database (GB)"), fieldtype: "Int", default: 2 },
		{ fieldname: "credits_a_month", label: __("Credits a Month"), fieldtype: "Int", default: 2000 },
	],
	formatter(value, row, column, data, default_formatter) {
		const shown = default_formatter(value, row, column, data);
		if (column.fieldname === "verdict" && data && data.verdict === __("Cheapest")) return `<span class="text-success">${shown}</span>`;
		return shown;
	},
};
