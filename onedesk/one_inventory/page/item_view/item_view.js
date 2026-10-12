// An item's page, opened at the item's own address (/desk/item/<name>;
// project_new.js hands the route here). Its body is the onedesk.item island
// (frontend/src/item); desk keeps the head (onedesk.island_page).

frappe.pages["item-view"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.item",
		title: __("Item"),
		parent: { label: __("Items"), route: "/desk/item" },
		// Edit Details and the documents started from an item (item_actions.js).
		requires: ["/assets/onedesk/js/project_actions.js", "/assets/onedesk/js/item_actions.js", "/assets/onedesk/js/lots_actions.js"],
		hide_sidebar: !frappe.is_mobile(),
		record: "Item",
		files: "files",
	});
};

// The page's head carries the item's picture, so the sidebar's goes.
onedesk.record.sidebar_parts.Item = [(frm) => frm.sidebar.image_section.addClass("hide")];
