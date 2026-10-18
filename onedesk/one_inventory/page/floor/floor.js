
frappe.pages["floor"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.floor",
		title: __("Shop Floor"),
		requires: ["/assets/onedesk/js/project_actions.js", "/assets/onedesk/js/item_actions.js", "/assets/onedesk/js/floor_actions.js"],
	});
};
