// The reader's task timers on a page of their own, for a phone, which has no
// rail. On a wider screen they are the rail's Timers panel (desk.js `rail`).
frappe.pages["timers"].on_page_load = (wrapper) =>
	onedesk.island_page(wrapper, { island: "onedesk.timers", title: __("Timers"), mark: "onetask" });
