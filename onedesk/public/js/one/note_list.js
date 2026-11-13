// Announcements are frappe's Note list (one/announcements.py), opening on
// what is showing; Status is a standard filter, so Ended is one pick away.
frappe.listview_settings["Note"] = {
	...frappe.listview_settings["Note"],
	add_fields: ["public", "one_status"],
	filters: [["one_status", "=", "Showing"]],
	get_indicator(doc) {
		if (!doc.public) return [__("Private"), "gray", "public,=,0"];
		return doc.one_status === "Ended" ? [__("Ended"), "gray", "one_status,=,Ended"] : [__("Showing"), "green", "one_status,=,Showing"];
	},
	onload(list) {
		list.page.set_title(__("Announcements"));
		if (!frappe.user.has_role("Workspace Administrator")) return;
		list.page.add_actions_menu_item(__("Stop Showing"), async () => {
			const names = list.get_checked_items().map((one) => one.name);
			for (const name of names) await frappe.xcall("onedesk.one.announcements.stop", { name });
			list.refresh();
		});
	},
};
