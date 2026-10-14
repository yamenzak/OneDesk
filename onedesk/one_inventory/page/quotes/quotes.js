// Quotes: asking suppliers for prices, their answers and the comparison, as
// one page. Its body is the onedesk.quotes island (frontend/src/quotes); desk
// keeps the head and OneInventory's rail (onedesk.island_page). Ask for
// Prices, Add Their Quote and the orders are quotes_actions.js, each on
// ERPNext's own mappers (one_inventory/quotes.py).

frappe.pages["quotes"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.quotes",
		views: "quotes",
		title: __("Request for Quotation"),
		requires: ["/assets/onedesk/js/quotes_actions.js"],
	});
};
