// A stage whose outcome is Lost is reached through Declare Lost, which asks why.
// See one_crm/stages.py.
frappe.ui.form.on("Opportunity", {
	async sales_stage(frm) {
		const stage = frm.doc.sales_stage;
		if (!stage || frm.is_new() || frm.doc.status === "Lost") return;
		const { message } = await frappe.db.get_value("Sales Stage", stage, "one_outcome");
		if (message?.one_outcome !== "Lost") return;
		await frm.set_value("sales_stage", frm.one_stage || "");
		frm.trigger("set_as_lost_dialog");
	},
	refresh(frm) {
		frm.one_stage = frm.doc.sales_stage;
		// Close is neither won nor lost, so a closed deal sat in an open stage on
		// the board and out of every total; Declare Lost says why instead. And a
		// deal is not where anybody buys from a supplier.
		frm.remove_custom_button(__("Close"));
		frm.remove_custom_button(__("Supplier Quotation"), __("Create"));
		frm.remove_custom_button(__("Request For Quotation"), __("Create"));
		onedesk.next_step.button(frm);
		onedesk.record_calendar(frm);
		onedesk.crm_record.refresh(frm);
	},
});
