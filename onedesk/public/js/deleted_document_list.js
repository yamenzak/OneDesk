// The Recycle Bin (one/recycle.py): who deleted what, and putting it back through
// One's restore rather than frappe's, which is its System Manager's.
frappe.listview_settings["Deleted Document"] = {
	...frappe.listview_settings["Deleted Document"],
	add_fields: ["deleted_doctype", "deleted_name", "one_title", "restored", "owner"],
	formatters: {
		// Its title, kept as it was deleted (one/recycle.py), and a custom
		// field's form, from its name "Form-fieldname".
		one_title(value, df, doc) {
			const name = String(doc.deleted_name ?? "");
			value = value || name;
			if (doc.deleted_doctype !== "Custom Field" || !name.includes("-")) return frappe.utils.escape_html(value);
			return frappe.utils.escape_html(__("{0} on {1}", [value, __(name.slice(0, name.lastIndexOf("-")))]));
		},
		deleted_doctype: (value) => frappe.utils.escape_html(value === "Record Type" ? __("Custom Collection") : __(value)),
	},
	get_indicator: (doc) => (doc.restored ? [__("Restored"), "green", "restored,=,1"] : [__("Deleted"), "red", "restored,=,0"]),
	onload(list) {
		list.page.set_title(__("Recycle Bin"));
		list.page.add_actions_menu_item(__("Restore"), async () => {
			const names = list.get_checked_items().map((one) => one.name);
			if (!names.length) return;
			const said = await frappe.xcall("onedesk.one.recycle.bulk_restore", { names });
			const parts = [];
			if (said.restored.length) parts.push(__("{0} restored.", [said.restored.length]));
			if (said.already.length) parts.push(__("{0} were already restored.", [said.already.length]));
			if (said.failed.length) parts.push(__("{0} couldn't be restored.", [said.failed.length]));
			frappe.show_alert({ message: parts.join(" "), indicator: said.failed.length ? "orange" : "green" });
			list.refresh();
		});
	},
};
