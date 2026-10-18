frappe.listview_settings["Record Type"] = {
	add_fields: ["record_doctype", "app", "rail_group"],
	hide_name_column: true,
	hide_name_filter: true,
	formatters: {
		record_doctype: (value) => frappe.utils.escape_html(__(value || "")),
	},
	onload(list) {
		const admin = frappe.user.has_role("Workspace Administrator");
		list.set_primary_action = () => {
			if (!admin) return;
			list.page.set_primary_action(
				__("Add Collection"),
				() => onedesk.oneai.open({ ask: __("I want a new collection.") }),
				"plus",
			);
		};
		list.set_primary_action();
		list.set_actions_menu_items = () => {
			list.page.clear_actions_menu();
			if (!admin) return;
			list.page.add_actions_menu_item(__("Change"), () => {
				const names = list.get_checked_items().map((doc) => __(doc.record_doctype));
				onedesk.oneai.open({ ask: __("I want to change {0}.", [names.join(", ")]) });
			}, false);
			list.page.add_actions_menu_item(__("Move"), () => move(list), false);
			const remove = list.get_actions_menu_items().find((item) => item.label === __("Delete"));
			if (remove) list.page.add_actions_menu_item(remove.label, remove.action, remove.standard);
		};
		list.set_actions_menu_items();
		if (!list.__one_opens) {
			list.__one_opens = true;
			list.$result[0].addEventListener(
				"click",
				(event) => {
					const $target = $(event.target);
					const $row = $target.closest(".list-row");
					if (!$row.length || $target.is(":checkbox, .list-row-like, .filterable") || event.ctrlKey || event.metaKey) return;
					const name = $row.find(".list-row-checkbox").attr("data-name");
					const doc = (list.data || []).find((one) => one.name === name);
					if (!doc) return;
					event.preventDefault();
					event.stopPropagation();
					frappe.set_route("List", doc.record_doctype);
				},
				true,
			);
		}
	},
};

function move(list) {
	const [doc] = list.get_checked_items();
	if (!doc || list.get_checked_items().length > 1) {
		frappe.show_alert({ message: __("Select one collection"), indicator: "orange" });
		return;
	}
	const dialog = new frappe.ui.Dialog({
		title: __("Move {0}", [__(doc.record_doctype)]),
		fields: [
			{
				fieldname: "app",
				fieldtype: "Select",
				label: __("App"),
				options: frappe.meta.get_docfield("Record Type", "app").options,
				default: doc.app,
				reqd: 1,
				change: () => groups(dialog.get_value("app")),
			},
			{ fieldname: "group", fieldtype: "Autocomplete", label: __("Group"), default: doc.rail_group || __("Your Records") },
		],
		primary_action_label: __("Move"),
		primary_action: async ({ app, group }) => {
			const where = await frappe.xcall("onedesk.one_studio.record_types.move", { record_type: doc.name, app, group });
			dialog.hide();
			frappe.show_alert({ message: __("Moved to {0}", [where]), indicator: "green" });
			list.refresh();
		},
	});
	const groups = async (app) => {
		const have = await frappe.xcall("onedesk.one_studio.record_types.groups_of", { app });
		dialog.set_df_property("group", "options", have);
		dialog.fields_dict.group.set_data(have);
	};
	groups(doc.app);
	dialog.show();
}
