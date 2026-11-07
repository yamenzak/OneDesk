frappe.pages["onefactory"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.factory",
		title: __("OneFactory"),
	});
};
