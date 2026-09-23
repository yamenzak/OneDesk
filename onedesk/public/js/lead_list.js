// Loaded after erpnext's own, which replaces the settings object whole.
(() => {
	const settings = (frappe.listview_settings["Lead"] ||= {});
	settings.formatters = { ...settings.formatters, ...onedesk.next_step.formatters };
})();
