// OneCRM's Home: how selling is going, what needs the reader today, and
// everything in OneCRM with what it is for. Its body is the onedesk.crm
// island (frontend/src/home); desk keeps the head and OneCRM's rail
// (onedesk.island_page). /desk/onecrm/reports and /desk/onecrm/setup open their
// part of it (one_crm/home.py, one_crm/story.py).

frappe.pages["onecrm"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.crm",
		title: __("OneCRM"),
	});
};
