frappe.pages["oneadmin-billing"].on_page_load = (wrapper) =>
	onedesk.island_page(wrapper, { island: "onedesk.oneadmin_billing", title: __("Billing"), mark: "oneadmin" });
