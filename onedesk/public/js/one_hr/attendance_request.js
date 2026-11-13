frappe.ui.form.on("Attendance Request", {
	refresh(frm) {
		frm.set_query("one_reason", () => ({ filters: { enabled: 1 } }));
	},
});
