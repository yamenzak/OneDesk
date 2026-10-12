// Sent Out: work a supplier does on our own materials, powder coating say,
// as one page. Its body is the onedesk.sent_out island (frontend/src/sent_out);
// desk keeps the head and OneInventory's rail (onedesk.island_page). Send
// Materials, Receive Back and the orders are sent_out_actions.js, each on
// ERPNext's own calls (one_inventory/sent_out.py).

frappe.pages["sent-out"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.sent_out",
		title: __("Sent Out"),
		requires: ["/assets/onedesk/js/sent_out_actions.js"],
	});
};
