frappe.ui.form.on("Project Template", {
	refresh(frm) {
		if (frm.is_new() || frm.doc.disabled || !frappe.model.can_create("Project")) return;
		frm.add_custom_button(__("New Project"), () =>
			frappe.new_doc("Project", { project_template: frm.doc.name, project_type: frm.doc.project_type })
		);
	},
});
