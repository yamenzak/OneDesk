// A signup, from the operator's side. Where it stands, what that means and
// Build Workspace are its Record Head (one_admin/heads.py); this is the way
// from a request to the workspace it became.
frappe.ui.form.on("Account Request", {
	refresh(frm) {
		if (frm.is_new() || !frm.doc.tenant) return;
		frm.add_custom_button(__("Open Workspace"), () => frappe.set_route("Form", "Tenant", frm.doc.tenant));
	},
});
