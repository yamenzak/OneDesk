// What the Upkeep page (one_inventory/page/upkeep) does, asked in frappe's
// own dialogs. `done` reads the page again.
frappe.provide("onedesk.upkeep");

// A service recorded as done: the day and what was done, saved on ERPNext's
// own log and submitted, which works out the job's next date.
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

// Something broken: ERPNext's own repair, opened new.
onedesk.upkeep.broken = (asset) => frappe.new_doc("Asset Repair", asset ? { asset } : {});

// A plan for an asset's servicing: ERPNext's own schedule, opened new.
onedesk.upkeep.plan = () => frappe.new_doc("Asset Maintenance");
