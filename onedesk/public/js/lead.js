frappe.ui.form.on("Lead", {
	refresh(frm) {
		onedesk.next_step.button(frm);
	},
});
