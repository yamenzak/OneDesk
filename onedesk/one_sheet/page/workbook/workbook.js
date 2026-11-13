frappe.pages["workbook"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.workbook",
		title: __("OneSheet"),
		hide_sidebar: true,
		bare: "one-workbook-page",
	});
};
