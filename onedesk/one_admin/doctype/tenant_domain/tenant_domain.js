frappe.ui.form.on("Tenant Domain", {
	refresh(frm) {
		frm.toggle_display(["status", "problem", "is_main"], false);
		frm.sidebar.sidebar.find(".form-shared").addClass("hidden");
	},
});
