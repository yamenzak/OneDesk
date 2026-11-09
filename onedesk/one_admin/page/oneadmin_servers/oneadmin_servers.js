frappe.pages["oneadmin-servers"].on_page_load = (wrapper) =>
	onedesk.island_page(wrapper, { island: "onedesk.oneadmin_servers", title: __("Servers"), mark: "oneadmin" });
