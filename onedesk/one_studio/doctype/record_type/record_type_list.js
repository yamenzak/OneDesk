// Custom Collections: what the workspace keeps of its own. A collection is
// made and changed by asking OneAI, and a click on one opens its records.
frappe.listview_settings["Record Type"] = {
	add_fields: ["record_doctype"],
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
			// frappe's own Delete, with its confirmation.
			const remove = list.get_actions_menu_items().find((item) => item.label === __("Delete"));
			if (remove) list.page.add_actions_menu_item(remove.label, remove.action, remove.standard);
		};
		list.set_actions_menu_items();
		// A row is not a page to read: it opens the collection's records. Caught
		// before frappe's own click, which would follow the row's link.
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
