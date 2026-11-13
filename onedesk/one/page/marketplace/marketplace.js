// OneMarketplace (one/marketplace.py): every app with its page, and
// Install or Turn Off for the workspace's administrators.
frappe.pages["marketplace"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.marketplace",
		title: onedesk.names.of("one_marketplace"),
	});
};
