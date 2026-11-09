frappe.pages["oneadmin"].on_page_load = (wrapper) =>
	onedesk.island_page(wrapper, { island: "onedesk.oneadmin", title: __("Overview"), mark: "oneadmin" });
