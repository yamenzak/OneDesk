frappe.pages["oneadmin-sessions"].on_page_load = (wrapper) =>
	onedesk.island_page(wrapper, { island: "onedesk.oneadmin_sessions", title: __("Sessions"), mark: "oneadmin" });
