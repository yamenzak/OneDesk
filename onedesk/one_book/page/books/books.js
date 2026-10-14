// OneBook's Home: how the money is doing, what needs somebody today, and
// everything in OneBook with what it is for. Its body is the onedesk.books
// island (frontend/src/home); desk keeps the head and OneBook's rail
// (onedesk.island_page). /desk/books/reports and /desk/books/setup open their
// part of it (one_book/home.py, one_book/story.py).

frappe.pages["books"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.books",
		title: __("OneBook"),
	});
};
