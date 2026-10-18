
frappe.pages["onehr"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.hr",
		title: __("OneHR"),
	});
};
