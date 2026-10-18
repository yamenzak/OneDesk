
frappe.pages["to-order"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.to_order",
		title: __("Reorder"),
	});
};
