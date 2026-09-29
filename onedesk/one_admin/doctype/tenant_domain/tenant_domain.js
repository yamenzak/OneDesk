// A customer's domain, from the operator's side: read-only, its head says
// whether it works, in the customer's words, and what has to happen for it
// to (heads.py `domain_said`), so the fields that say the same are not shown
// twice. Only operators read it, so sharing it gives nobody anything.
frappe.ui.form.on("Tenant Domain", {
	refresh(frm) {
		frm.toggle_display(["status", "problem", "is_main"], false);
		frm.sidebar.sidebar.find(".form-shared").addClass("hidden");
	},
});
