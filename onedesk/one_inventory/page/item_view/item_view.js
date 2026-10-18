
frappe.pages["item-view"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.item",
		title: __("Item"),
		parent: { label: __("Items"), route: "/desk/item" },
		requires: ["/assets/onedesk/js/project_actions.js", "/assets/onedesk/js/item_actions.js", "/assets/onedesk/js/lots_actions.js"],
		hide_sidebar: !frappe.is_mobile(),
		record: "Item",
		files: "files",
	});
};

onedesk.record.sidebar_parts.Item = [(frm) => frm.sidebar.image_section.addClass("hide")];
