
frappe.pages["stock-on-hand"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.stock",
		title: __("Stock Summary"),
		requires: ["/assets/onedesk/js/project_actions.js", "/assets/onedesk/js/item_actions.js"],
	});
};
