// The Recycle Bin (one/recycle.py): what was deleted, and putting it back.
frappe.pages["recycle-bin"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.recycle_bin",
		title: __("Recycle Bin"),
	});
};
