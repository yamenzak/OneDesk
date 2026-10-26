// Dashboards (one/dashboards.py): every dashboard the reader may read.
frappe.pages["dashboards"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.dashboards",
		title: __("Dashboards"),
	});
};
