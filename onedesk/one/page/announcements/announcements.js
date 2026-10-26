// Announcements (one/announcements.py): what the office has said.
frappe.pages["announcements"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.announcements",
		title: __("Announcements"),
	});
};
