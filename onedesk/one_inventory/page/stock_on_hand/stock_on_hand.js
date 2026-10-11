// Stock on Hand: what the stores hold now, in every warehouse or one. Its
// body is the onedesk.stock island (frontend/src/stock); desk keeps the head
// and OneInventory's rail (onedesk.island_page).

frappe.pages["stock-on-hand"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.stock",
		title: __("Stock on Hand"),
		// Move Stock, Count Stock and Add Warehouse (item_actions.js).
		requires: ["/assets/onedesk/js/project_actions.js", "/assets/onedesk/js/item_actions.js"],
	});
};
