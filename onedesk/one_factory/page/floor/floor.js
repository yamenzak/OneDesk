
frappe.pages["floor"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.floor",
		title: __("Shop Floor"),
		requires: ["/assets/onedesk/js/one_project/project_actions.js", "/assets/onedesk/js/one_inventory/item_actions.js", "/assets/onedesk/js/one_factory/floor_actions.js"],
	});
};
