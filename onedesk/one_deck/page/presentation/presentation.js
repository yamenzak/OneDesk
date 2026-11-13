frappe.pages["presentation"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.presentation",
		title: onedesk.names.of("one_deck"),
		hide_sidebar: true,
		bare: "one-presentation-page",
	});
};
