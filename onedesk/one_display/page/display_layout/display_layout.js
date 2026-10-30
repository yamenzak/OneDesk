frappe.pages["display-layout"].on_page_load = (wrapper) =>
	onedesk.island_page(wrapper, { island: "onedesk.display_layout", title: __("Layout"), mark: "onedisplay", fit: true });
