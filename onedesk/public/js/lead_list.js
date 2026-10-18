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
	settings.filters = [["status", "in", ["Lead", "Open", "Replied", "Interested"]]];
})();
