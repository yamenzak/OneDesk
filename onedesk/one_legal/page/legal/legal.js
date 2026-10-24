frappe.pages["legal"].on_page_load = (wrapper) =>
	onedesk.island_page(wrapper, { island: "onedesk.legal", title: __("Agreements"), parent: { label: __("Agreements"), route: "/desk/legal" } });
