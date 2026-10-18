
frappe.pages["lots"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.lots",
		views: "lots",
		title: __("Batch and Serial No"),
		requires: ["/assets/onedesk/js/lots_actions.js"],
	});
};
