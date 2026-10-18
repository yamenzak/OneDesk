(() => {
	const hours = (value) =>
		__("{0} h", [format_number(value || 0, null, Number(value) % 1 ? 1 : 0)]);
	const day = (value) => frappe.datetime.str_to_user(value);
	frappe.listview_settings["Timesheet"] = Object.assign(frappe.listview_settings["Timesheet"] || {}, {
		hide_name_column: true,
		add_fields: ["end_date"],
		formatters: {
			start_date(value, df, doc) {
				if (!value) return "";
				return doc.end_date && doc.end_date !== value ? `${day(value)} – ${day(doc.end_date)}` : day(value);
			},
			total_hours: (value) => hours(value),
			total_billable_hours: (value) => (Number(value) ? hours(value) : `<span class="text-muted">–</span>`),
		},
	});
})();
