frappe.pages["display-slides"].on_page_load = (wrapper) =>
	onedesk.island_page(wrapper, { island: "onedesk.display_slides", title: __("Slides"), mark: "onedisplay", fit: true });
