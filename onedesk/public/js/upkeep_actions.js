frappe.provide("onedesk.upkeep");

onedesk.upkeep.done = (service, what, done) => {
	const dialog = new frappe.ui.Dialog({
		title: __("Mark Done"),
		fields: [
			{ fieldtype: "Date", fieldname: "on", label: __("Completion Date"), default: frappe.datetime.get_today(), reqd: 1 },
			{ fieldtype: "Small Text", fieldname: "notes", label: __("Actions Performed") },
		],
		primary_action_label: __("Mark Done"),
		primary_action: async (values) => {
			await frappe.xcall("onedesk.one_inventory.upkeep.done", { service, on: values.on, notes: values.notes || null });
			dialog.hide();
			frappe.show_alert({ message: __("{0} is done", [what]), indicator: "green" });
			done?.();
		},
	});
	dialog.show();
};

onedesk.upkeep.broken = (asset) => frappe.new_doc("Asset Repair", asset ? { asset } : {});

onedesk.upkeep.plan = () => frappe.new_doc("Asset Maintenance");
