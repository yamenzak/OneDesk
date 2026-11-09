frappe.pages["oneadmin-status"].on_page_load = (wrapper) =>
	onedesk.island_page(wrapper, { island: "onedesk.oneadmin_status", title: __("Status"), mark: "oneadmin" });
