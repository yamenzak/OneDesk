frappe.pages["timers"].on_page_load = (wrapper) =>
	onedesk.island_page(wrapper, { island: "onedesk.timers", title: __("Timers"), mark: "onetask" });
