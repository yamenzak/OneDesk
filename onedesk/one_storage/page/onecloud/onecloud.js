frappe.pages["onecloud"].on_page_load = (wrapper) =>
	onedesk.island_page(wrapper, {
		island: "onedesk.onecloud",
		title: __("OneCloud"),
		mark: "onestorage",
		fit: true,
		requires: onedesk.cloud_assets,
	});
