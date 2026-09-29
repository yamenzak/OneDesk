// A log row, reached only by a link: its list opens the workspace instead.
// Only operators read it, so sharing it gives nobody anything.
frappe.ui.form.on("Tenant Event", {
	refresh(frm) {
		frm.sidebar.sidebar.find(".form-shared").addClass("hidden");
	},
});
