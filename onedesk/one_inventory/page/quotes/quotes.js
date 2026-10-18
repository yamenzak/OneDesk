
frappe.pages["quotes"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.quotes",
		views: "quotes",
		title: __("Request for Quotation"),
		requires: ["/assets/onedesk/js/quotes_actions.js"],
	});
};
