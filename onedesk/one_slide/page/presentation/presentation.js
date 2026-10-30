frappe.pages["presentation"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.presentation",
		title: __("OneSlide"),
		hide_sidebar: true,
		bare: "one-presentation-page",
	});
};
