frappe.pages["onemail"].on_page_load = (wrapper) =>
	onedesk.island_page(wrapper, { island: "onedesk.onemail", title: onedesk.names.of("one_mail"), mark: "onemail", fit: true });
