// Custom Fields: every field the workspace added or changed, one row a field.
// A row opens its form's Customize page, and a field is added or changed by
// asking OneAI, so Add opens the panel rather than a new record.
frappe.listview_settings["Workspace Field"] = {
	add_fields: ["status", "form", "app"],
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
	get_form_link(doc) {
		return `/desk/customize/${encodeURIComponent(doc.form)}`;
	},
	primary_action() {
		onedesk.oneai.open({ ask: __("I want to add a field.") });
	},
	onload(list) {
		// frappe would say "Add Workspace Field"; the button says what it does.
		list.set_primary_action = () =>
			list.page.set_primary_action(__("Add Field"), () => this.primary_action(), "plus");
		list.set_primary_action();
		// A field changes through a OneAI card or a Reset, which tell any
		// Customize page open on the form; the list hears the same.
		frappe.realtime.off("one_customized", list.__one_customized);
		list.__one_customized = () => list.refresh();
		frappe.realtime.on("one_customized", list.__one_customized);
	},
};
