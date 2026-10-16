// OneHR's Home: everybody's day, and for HR how the people are doing, then
// everything in OneHR with what it is for. Its body is the onedesk.hr island
// (frontend/src/home); desk keeps the head and OneHR's rail
// (onedesk.island_page). /desk/onehr/reports and /desk/onehr/setup open their
// part of it (one_hr/home.py, one_hr/story.py).

frappe.pages["onehr"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.hr",
		title: __("OneHR"),
	});
};
