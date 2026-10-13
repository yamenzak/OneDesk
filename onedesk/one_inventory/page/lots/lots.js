// Lots: batches and serial numbers as one tool, what each lot holds and
// where, which go off soon, and the items kept in lots. Its body is the
// onedesk.lots island (frontend/src/lots); desk keeps the head and
// OneInventory's rail (onedesk.island_page). Track Lots and New Lot are
// lots_actions.js, which an item's Stock tab uses too (one_inventory/lots.py).

frappe.pages["lots"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.lots",
		views: "lots",
		title: __("Lots"),
		requires: ["/assets/onedesk/js/lots_actions.js"],
	});
};
