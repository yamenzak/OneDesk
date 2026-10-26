// One's Home (one/home.py): what waits for the reader, and for an
// administrator what in the workspace needs them.
frappe.pages["one"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.one_home",
		title: __("Home"),
	});
};
