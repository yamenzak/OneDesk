frappe.ui.form.on("Project Template", {
	refresh(frm) {
		const field = frm.fields_dict.one_tasks_part;
		frm.toggle_display("one_tasks_part", !frm.is_new());
		frm.toggle_display("tasks", frm.is_new());
		if (field && !frm.is_new()) {
			const props = { template: frm.doc.name, frm };
			if (field.one_island) field.one_island.update(props);
			else {
				field.$wrapper.empty();
				field.one_island = frappe.ui.mount_island("onedesk.template_part", field.$wrapper[0], props);
			}
		}
		if (frm.is_new() || frm.doc.disabled || !frappe.model.can_create("Project")) return;
		frm.add_custom_button(__("New Project"), () =>
			frappe.new_doc("Project", { project_template: frm.doc.name, project_type: frm.doc.project_type })
		);
	},
});
