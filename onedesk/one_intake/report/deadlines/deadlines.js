// Every date something must be done by, from what was read. See deadlines.py.
frappe.query_reports["Deadlines"] = {
	filters: [
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date", reqd: 1, default: frappe.datetime.get_today() },
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date", reqd: 1, default: frappe.datetime.add_days(frappe.datetime.get_today(), 90) },
		{
			fieldname: "source",
			label: __("From"),
			fieldtype: "Select",
			options: ["", "Documents", "Contracts", "Employees"].map((value) => ({ value, label: value ? __(value) : "" })),
		},
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "days" && data && data.days <= 7) return `<span class="text-ink-red-4">${value}</span>`;
		if (column.fieldname === "title" && data && data.doctype && data.name) {
			const route = `/desk/${frappe.router.slug(data.doctype)}/${encodeURIComponent(data.name)}`;
			return `<a href="${route}">${value}</a>`;
		}
		return value;
	},
};
