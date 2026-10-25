frappe.pages["intake"].on_page_load = (wrapper) =>
	onedesk.island_page(wrapper, { island: "onedesk.intake", title: __("Documents"), mark: "oneai" });
