// Bills of Materials: the item with room for its name, where each stands,
// whether it has steps and what one costs. Whether it has steps said as a
// word, where frappe drew a checkbox that looked like one to tick.
(() => {
	const settings = (frappe.listview_settings["BOM"] = frappe.listview_settings["BOM"] || {});
	settings.formatters = Object.assign(settings.formatters || {}, {
		with_operations(value) {
			return value ? frappe.utils.escape_html(__("Yes")) : '<span class="text-muted">–</span>';
		},
	});
})();
