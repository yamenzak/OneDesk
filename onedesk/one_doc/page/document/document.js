frappe.pages["document"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.document",
		title: onedesk.names.of("one_doc"),
		hide_sidebar: true,
		bare: "one-document-page",
	});
};
