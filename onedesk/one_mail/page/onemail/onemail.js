frappe.pages["onemail"].on_page_load = (wrapper) =>
	onedesk.island_page(wrapper, { island: "onedesk.onemail", title: __("OneMail"), mark: "onemail", fit: true });
