// Plant Floor: a floor's workstations, each with its status and what is
// running on it, and the stock kept on the floor. Its body is the
// onedesk.plant island (frontend/src/plant); desk keeps the head and
// OneInventory's rail (onedesk.island_page). It stands for ERPNext's Visual
// Plant Floor, whose calls it makes (one_inventory/plant.py).

frappe.pages["plant"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.plant",
		title: __("Plant Floor"),
		// Change a status, add or move stock (plant_actions.js).
		requires: ["/assets/onedesk/js/plant_actions.js"],
	});
};
