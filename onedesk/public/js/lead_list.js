// Loaded after erpnext's own, which replaces the settings object whole.
// Each status in the colour of what it means, as Frappe CRM's statuses are:
// frappe's guess paints Open red, as if something were wrong.
(() => {
	const settings = (frappe.listview_settings["Lead"] ||= {});
	settings.formatters = { ...settings.formatters, ...onedesk.next_step.formatters };
	const COLOUR = {
		Lead: "blue",
		Open: "blue",
		Replied: "orange",
		Interested: "orange",
		Opportunity: "purple",
		Quotation: "purple",
		Converted: "green",
		"Lost Quotation": "gray",
		"Do Not Contact": "gray",
	};
	settings.get_indicator = (doc) => [__(doc.status), COLOUR[doc.status] || "gray", `status,=,${doc.status}`];
	// The list opens on what is still being worked (next.py's OPEN).
	settings.filters = [["status", "in", ["Lead", "Open", "Replied", "Interested"]]];
})();
