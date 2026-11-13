
frappe.pages["stock-on-hand"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.stock",
		title: __("Stock Summary"),
		requires: ["/assets/onedesk/js/one_project/project_actions.js", "/assets/onedesk/js/one_inventory/item_actions.js"],
	});
};
