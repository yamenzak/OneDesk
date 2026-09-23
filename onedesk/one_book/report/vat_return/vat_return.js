// Tax charged against tax paid, for a period. See vat_return.py.
frappe.query_reports["VAT Return"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.quarter_start(),
		},
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date", reqd: 1, default: frappe.datetime.get_today() },
	],
	formatter(value, row, column, data, default_formatter) {
		// A heading or a total has no rate or amount of its own: blank, not nought.
		if (value === undefined || value === null) return "";
		const out = default_formatter(value, row, column, data);
		if (data && data.sub && column.fieldname === "line") return `<span style="padding-left: var(--padding-lg)">${out}</span>`;
		return data && data.bold ? `<strong>${out}</strong>` : out;
	},
};
