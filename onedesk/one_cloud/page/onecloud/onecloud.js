frappe.pages["onecloud"].on_page_load = (wrapper) =>
	onedesk.island_page(wrapper, {
		island: "onedesk.onecloud",
		title: onedesk.names.of("one_cloud"),
		mark: "onecloud",
		fit: true,
		requires: onedesk.cloud_assets,
	});
