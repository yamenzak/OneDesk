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
		frm.remove_custom_button(__("Close"));
		if (!["Closed", "Lost"].includes(frm.doc.status)) frm.remove_custom_button(__("Reopen"));
		frm.remove_custom_button(__("Supplier Quotation"), __("Create"));
		frm.remove_custom_button(__("Request For Quotation"), __("Create"));
		frm.toggle_display(["total", "base_total"], (frm.doc.items || []).length > 0);
		onedesk.next_step.button(frm);
		onedesk.record_calendar(frm);
		onedesk.crm_record.refresh(frm);
	},
});
