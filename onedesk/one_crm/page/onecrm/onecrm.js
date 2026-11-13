
frappe.pages["onecrm"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.crm",
		title: onedesk.names.of("one_crm"),
	});
};
