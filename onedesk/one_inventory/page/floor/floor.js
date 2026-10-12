// Shop Floor: the work on the floor, each work order with how far its steps
// have got and each step's job card to start, pause, record and close. Its
// body is the onedesk.floor island (frontend/src/floor); desk keeps the head
// and OneInventory's rail (onedesk.island_page). It stands for ERPNext's own
// Shop Floor page, whose calls it makes (one_inventory/floor.py).

frappe.pages["floor"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.floor",
		title: __("Shop Floor"),
		// Start, record and check a step (floor_actions.js); Finish a work
		// order (item_actions.js).
		requires: ["/assets/onedesk/js/project_actions.js", "/assets/onedesk/js/item_actions.js", "/assets/onedesk/js/floor_actions.js"],
	});
};
