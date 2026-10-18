
frappe.pages["plant"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.plant",
		title: __("Plant Floor"),
		requires: ["/assets/onedesk/js/plant_actions.js"],
	});
};
