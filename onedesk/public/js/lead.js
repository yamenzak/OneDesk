frappe.ui.form.on("Lead", {
	refresh(frm) {
		onedesk.next_step.button(frm);
		onedesk.crm_record.refresh(frm);
	},
});
