frappe.pages["boards"].on_page_load = (wrapper) =>
	onedesk.island_page(wrapper, { island: "onedesk.boards", title: __("Boards"), mark: "onedisplay" });
