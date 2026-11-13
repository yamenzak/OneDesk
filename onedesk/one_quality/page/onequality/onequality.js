frappe.pages["onequality"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.quality",
		title: onedesk.names.of("one_quality"),
	});
};
