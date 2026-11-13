frappe.ui.form.on("Lead", {
	refresh(frm) {
		onedesk.record_calendar(frm);
		onedesk.next_step.button(frm);
		onedesk.crm_record.refresh(frm);
	},
	onload_post_render(frm) {
		onedesk.crm_record.one_series(frm);
	},
});
