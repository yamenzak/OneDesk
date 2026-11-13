
frappe.pages["books"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.books",
		title: onedesk.names.of("one_book"),
	});
};
