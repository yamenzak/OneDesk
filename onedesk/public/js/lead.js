frappe.ui.form.on("Lead", {
	refresh(frm) {
		onedesk.record_calendar(frm);
		onedesk.next_step.button(frm);
		onedesk.crm_record.refresh(frm);
	},
	// erpnext's Lead shows its Series from its class's refresh, which runs after
	// this one; onload_post_render runs after both.
	onload_post_render(frm) {
		onedesk.crm_record.one_series(frm);
	},
});
