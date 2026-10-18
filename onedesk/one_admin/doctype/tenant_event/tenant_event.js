frappe.ui.form.on("Tenant Event", {
	refresh(frm) {
		frm.sidebar.sidebar.find(".form-shared").addClass("hidden");
	},
});
