// OneHub (public/js/one_interface/centre.js, onedesk.centers.reachable):
// every centre the reader may open, a tile each, searchable.
frappe.pages["one-hub"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.hub",
		title: onedesk.names.of("one_hub"),
		mark: "one",
	});
};
