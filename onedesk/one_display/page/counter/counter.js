frappe.pages["counter"].on_page_load = (wrapper) =>
	onedesk.island_page(wrapper, { island: "onedesk.counter", title: __("Counter"), mark: "onedisplay" });
