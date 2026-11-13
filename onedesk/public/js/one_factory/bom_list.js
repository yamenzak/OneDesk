(() => {
	const settings = (frappe.listview_settings["BOM"] = frappe.listview_settings["BOM"] || {});
	settings.formatters = Object.assign(settings.formatters || {}, {
		with_operations(value) {
			return value ? frappe.utils.escape_html(__("Yes")) : '<span class="text-muted">–</span>';
		},
	});
})();
