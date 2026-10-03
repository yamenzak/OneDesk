// Custom Collections: what the workspace keeps of its own. A collection is
// never made by hand: Add Collection asks OneAI, which designs its fields.
frappe.listview_settings["Record Type"] = {
	hide_name_column: true,
	hide_name_filter: true,
	onload(list) {
		if (!frappe.user.has_role("Workspace Administrator")) return;
		list.set_primary_action = () =>
			list.page.set_primary_action(
				__("Add Collection"),
				() => onedesk.oneai.open({ ask: __("I want a new collection.") }),
				"plus",
			);
		list.set_primary_action();
	},
};
