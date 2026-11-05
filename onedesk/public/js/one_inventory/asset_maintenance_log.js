frappe.ui.form.on("Asset Maintenance Log", {
	refresh(frm) {
		if (frm.is_new() || frm.doc.docstatus !== 0 || !frappe.model.can_submit("Asset Maintenance Log")) return;
		frm.page.set_primary_action(__("Mark Done"), () => {
			const dialog = new frappe.ui.Dialog({
				title: __("Mark Done"),
				fields: [
					{ fieldtype: "Date", fieldname: "on", label: __("Completion Date"), default: frappe.datetime.get_today(), reqd: 1 },
					{ fieldtype: "Small Text", fieldname: "notes", label: __("Actions Performed"), default: frm.doc.actions_performed || "" },
				],
				primary_action_label: __("Mark Done"),
				primary_action: async (values) => {
					await frappe.xcall("onedesk.one_inventory.upkeep.done", { service: frm.doc.name, on: values.on, notes: values.notes || null });
					dialog.hide();
					frappe.show_alert({ message: __("{0} is done", [frm.doc.task_name || frm.doc.name]), indicator: "green" });
					frm.reload_doc();
				},
			});
			dialog.show();
		});
	},
});
