frappe.pages["oneadmin-releases"].on_page_load = (wrapper) =>
	onedesk.island_page(wrapper, { island: "onedesk.oneadmin_releases", title: __("Releases"), mark: "oneadmin" });
