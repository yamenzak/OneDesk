// A template's page starts a project from it. The tasks are ERPNext's to make:
// a project with a Project Template gets one for each when it is saved. See
// one_project/templates.py.
frappe.ui.form.on("Project Template", {
	refresh(frm) {
		if (frm.is_new() || frm.doc.disabled || !frappe.model.can_create("Project")) return;
		frm.add_custom_button(__("New Project"), () =>
			frappe.new_doc("Project", { project_template: frm.doc.name, project_type: frm.doc.project_type })
		);
	},
});
