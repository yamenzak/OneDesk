// Bill Progress on an order: the share of the work done, billed at the
// order's rate, less what's been billed and less retention. The invoice opens
// unsaved. See one_project/progress.py.
for (const doctype of ["Purchase Order", "Sales Order"]) {
	frappe.ui.form.on(doctype, {
		refresh(frm) {
			onedesk.progress.button(frm);
		},
	});
}

frappe.provide("onedesk.progress");

onedesk.progress.INVOICE = { "Purchase Order": "Purchase Invoice", "Sales Order": "Sales Invoice" };

onedesk.progress.button = (frm) => {
	const open = frm.doc.docstatus === 1 && !["Closed", "On Hold", "Completed"].includes(frm.doc.status);
	if (!open || flt(frm.doc.per_billed) >= 100) return;
	if (!frappe.model.can_create(onedesk.progress.INVOICE[frm.doctype])) return;
	frm.add_custom_button(__("Bill Progress"), () => onedesk.progress.ask(frm), __("Create"));
};

onedesk.progress.ask = async (frm) => {
	const said = await frappe.xcall("onedesk.one_project.progress.progress", {
		doctype: frm.doctype,
		name: frm.doc.name,
	});
	const dialog = new frappe.ui.Dialog({
		title: __("Bill Progress"),
		fields: [
			{ fieldtype: "Percent", fieldname: "done", label: __("Done"), reqd: 1, default: said.billed },
			{ fieldtype: "Column Break" },
			{ fieldtype: "Percent", fieldname: "billed", label: __("Billed So Far"), read_only: 1, default: said.billed },
			{
				fieldtype: "Percent",
				fieldname: "retention",
				label: __("Retention"),
				read_only: 1,
				default: said.retention,
				hidden: !said.retention,
			},
		],
		primary_action_label: __("Create"),
		primary_action: ({ done }) => {
			dialog.hide();
			frappe.model.open_mapped_doc({
				method: "onedesk.one_project.progress.bill_progress",
				source_name: frm.doc.name,
				args: { doctype: frm.doctype, done },
			});
		},
	});
	dialog.show();
};
