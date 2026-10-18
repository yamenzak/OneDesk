
frappe.pages["upkeep"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.upkeep",
		views: "upkeep",
		title: __("Asset Maintenance"),
		requires: ["/assets/onedesk/js/upkeep_actions.js"],
	});
};
