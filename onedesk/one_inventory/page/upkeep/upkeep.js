// Upkeep: servicing and mending the company's equipment as one page. Its
// body is the onedesk.upkeep island (frontend/src/upkeep); desk keeps the
// head and OneInventory's rail (onedesk.island_page). Mark Done and the new
// records are upkeep_actions.js (one_inventory/upkeep.py).

frappe.pages["upkeep"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.upkeep",
		views: "upkeep",
		title: __("Upkeep"),
		requires: ["/assets/onedesk/js/upkeep_actions.js"],
	});
};
