// The reason is picked from the enabled ones. What the request says and the
// Approve and Reject that answer it are its Record Head (one_hr/heads.py).
frappe.ui.form.on("Attendance Request", {
	refresh(frm) {
		frm.set_query("one_reason", () => ({ filters: { enabled: 1 } }));
	},
});
