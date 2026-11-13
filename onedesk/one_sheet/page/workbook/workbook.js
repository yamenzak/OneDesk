frappe.pages["workbook"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.workbook",
		title: onedesk.names.of("one_sheet"),
		hide_sidebar: true,
		bare: "one-workbook-page",
	});
};
