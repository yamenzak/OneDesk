
frappe.pages["item-view"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.item",
		title: __("Item"),
		parent: { label: __("Items"), route: "/desk/item" },
		requires: ["/assets/onedesk/js/project_actions.js", "/assets/onedesk/js/item_actions.js", "/assets/onedesk/js/lots_actions.js"],
		record: "Item",
		files: "files",
	});
};

// The page draws the item's picture, so the sidebar's goes, and its print,
// like and OneCloud sit beside the name, as on a record with no picture.
onedesk.record.sidebar_parts.Item = [
	(frm) => {
		const $likes = frm.sidebar.image_section.find(".form-stats-likes");
		if ($likes.length) frm.sidebar.sidebar.find(".sidebar-meta-details > .flex").first().append($likes);
		frm.sidebar.image_section.addClass("hide");
	},
];
