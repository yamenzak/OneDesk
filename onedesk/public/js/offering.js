// A plan, a credit pack or an add-on, from the operator's side. How many
// workspaces already bought it, which decides every edit here, is its Record
// Head's sentence (one_admin/heads.py).
frappe.ui.form.on("Offering", {
	enabled(frm) {
		if (frm.doc.enabled || frm.is_new()) return;
		frappe.show_alert({
			message: __("Existing workspaces keep what they bought. This only stops new signups."),
			indicator: "blue",
		});
	},
});
