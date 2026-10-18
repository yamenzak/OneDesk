
frappe.pages["sent-out"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.sent_out",
		views: "sent-out",
		title: __("Subcontracting Order"),
		requires: ["/assets/onedesk/js/sent_out_actions.js"],
	});
};
