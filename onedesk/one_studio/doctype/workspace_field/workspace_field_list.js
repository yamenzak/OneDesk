// Custom Fields: every field the workspace added or changed, one row a field.
// A field is added or changed by asking OneAI: Add Field and a click on a row
// open the panel, and the only actions are Export and Reset, per form.
frappe.listview_settings["Workspace Field"] = {
	add_fields: ["status", "form", "app", "label"],
	hide_name_column: true,
	hide_name_filter: true,
	get_indicator(doc) {
		return doc.status === "Changed"
			? [__("Changed"), "orange", "status,=,Changed"]
			: [__("Added"), "blue", "status,=,Added"];
	},
	formatters: {
		form: (value) => frappe.utils.escape_html(__(value || "")),
		fieldtype: (value) => frappe.utils.escape_html(__(value || "")),
	},
	primary_action() {
		onedesk.oneai.open({ ask: __("I want to add a field.") });
	},
	onload(list) {
		const settings = this;
		// frappe would say "Add Workspace Field"; the button says what it does.
		list.set_primary_action = () =>
			list.page.set_primary_action(__("Add Field"), () => settings.primary_action(), "plus");
		list.set_primary_action();
		list.set_actions_menu_items = () => {
			list.page.clear_actions_menu();
			list.page.add_actions_menu_item(__("Export"), () => settings.export(list), false);
			list.page.add_actions_menu_item(__("Reset"), () => settings.reset(list), false);
		};
		list.set_actions_menu_items();
		// A row is not a record to open: it asks OneAI to change the field. Caught
		// before frappe's own click, which would follow the row's link.
		if (!list.__one_asks) {
			list.__one_asks = true;
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
					onedesk.oneai.open({ ask: __("I want to change the field {0} on {1}.", [doc.label, __(doc.form)]) });
				},
				true,
			);
		}
		// A field changes through a OneAI card or a Reset; the list hears it.
		frappe.realtime.off("one_customized", list.__one_customized);
		list.__one_customized = () => list.refresh();
		frappe.realtime.on("one_customized", list.__one_customized);
	},
	// The forms of the ticked rows, each once.
	forms(list) {
		return [...new Set(list.get_checked_items().map((doc) => doc.form))];
	},
	async export(list) {
		for (const doctype of this.forms(list)) {
			const said = await frappe.xcall("onedesk.one.customize.export", { doctype });
			const blob = new Blob([JSON.stringify(said, null, 1)], { type: "application/json" });
			const link = Object.assign(document.createElement("a"), {
				href: URL.createObjectURL(blob),
				download: `${frappe.scrub(doctype)}-customized.json`,
			});
			link.click();
			URL.revokeObjectURL(link.href);
		}
	},
	reset(list) {
		const forms = this.forms(list);
		if (!forms.length) return;
		frappe.confirm(
			__("Reset {0}? This removes all custom fields and changes.", [forms.map((one) => __(one)).join(", ")]),
			async () => {
				for (const doctype of forms) await frappe.xcall("onedesk.one.customize.reset", { doctype });
				frappe.show_alert({ message: __("{0} reset", [forms.map((one) => __(one)).join(", ")]), indicator: "green" });
				list.clear_checked_items();
				list.refresh();
			},
		);
	},
};
