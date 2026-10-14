// To Order: what to buy, by supplier, and Order, a draft purchase order per
// supplier from the lines ticked. Its body is the onedesk.to_order island
// (frontend/src/to_order); desk keeps the head and OneInventory's rail
// (onedesk.island_page). See one_inventory/order.py.

frappe.pages["to-order"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.to_order",
		title: __("Reorder"),
	});
};
