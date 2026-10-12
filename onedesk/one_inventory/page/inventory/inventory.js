// OneInventory's Home: what needs somebody today, and everything in
// OneInventory with what it is for. Its body is the onedesk.home island
// (frontend/src/home); desk keeps the head and OneInventory's rail
// (onedesk.island_page). /desk/inventory/reports and /desk/inventory/setup
// open their part of it (one_inventory/home.py).

frappe.pages["inventory"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.home",
		title: __("OneInventory"),
	});
};
