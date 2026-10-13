// Stock Movements: the type, where from, where to, the project and what it
// moved. ERPNext leaves Total Amount empty for what makes goods, which the
// list drew as 0.00, so those rows show what was made instead. The number is
// left off: the type, date and value tell the rows apart, and it was cut.
(() => {
	const settings = (frappe.listview_settings["Stock Entry"] = frappe.listview_settings["Stock Entry"] || {});
	settings.hide_name_column = true;
	settings.add_fields = [...new Set([...(settings.add_fields || []), "purpose", "total_incoming_value"])];
	settings.formatters = Object.assign(settings.formatters || {}, {
		total_amount(value, df, doc) {
			const made = ["Manufacture", "Repack"].includes(doc.purpose);
			return frappe.format(made ? doc.total_incoming_value : value, df, null, doc);
		},
	});
})();
