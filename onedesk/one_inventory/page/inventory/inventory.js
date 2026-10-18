
frappe.pages["inventory"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.home",
		title: __("OneInventory"),
	});
};
