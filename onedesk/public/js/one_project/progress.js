for (const doctype of ["Purchase Order", "Sales Order"]) {
	frappe.ui.form.on(doctype, {
		refresh(frm) {
			onedesk.progress.button(frm);
		},
	});
}

frappe.ui.form.on("Sales Order", {
	async project(frm) {
		if (!frm.is_new() || !frm.doc.project || !frappe.boot.one_retention) return;
		const { message } = await frappe.db.get_value("Project", frm.doc.project, ["one_retention", "one_retention_due", "one_retention_handover"]);
		if (!flt(message?.one_retention)) return;
		frm.set_value({
			one_retention: message.one_retention,
			one_retention_due: frm.doc.one_retention_due || message.one_retention_due,
			one_retention_handover: message.one_retention_handover,
		});
	},
});

frappe.provide("onedesk.progress");

onedesk.progress.INVOICE = { "Purchase Order": "Purchase Invoice", "Sales Order": "Sales Invoice" };

onedesk.progress.button = (frm) => {
	const open = frm.doc.docstatus === 1 && !["Closed", "On Hold", "Completed"].includes(frm.doc.status);
	if (!open || flt(frm.doc.per_billed) >= 100) return;
	if (!frappe.model.can_create(onedesk.progress.INVOICE[frm.doctype])) return;
	frm.add_custom_button(__("Bill Progress"), () => onedesk.progress.ask(frm), __("Create"));
};

onedesk.progress.ask = async (frm, share) => {
	const said = await frappe.xcall("onedesk.one_project.progress.progress", {
		doctype: frm.doctype,
		name: frm.doc.name,
	});
	const several = said.lines.length > 1;
	const dialog = new frappe.ui.Dialog({
		title: __("Bill Progress"),
		size: several ? "large" : undefined,
		fields: [
			{
				fieldtype: "Percent",
				fieldname: "done",
				label: __("Done"),
				default: share || said.billed,
				depends_on: "eval:!doc.by_line",
				mandatory_depends_on: "eval:!doc.by_line",
			},
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
			{ fieldtype: "Section Break", hidden: !several },
			{ fieldtype: "Check", fieldname: "by_line", label: __("By Line") },
			{
				fieldtype: "Table",
				fieldname: "lines",
				label: __("Lines"),
				depends_on: "eval:doc.by_line",
				cannot_add_rows: true,
				cannot_delete_rows: true,
				in_place_edit: true,
				data: said.lines.map((one) => ({ ...one, done: one.billed })),
				fields: [
					{ fieldtype: "Data", fieldname: "line", hidden: 1 },
					{ fieldtype: "Data", fieldname: "item", label: __("Item"), read_only: 1, in_list_view: 1, columns: 4 },
					{ fieldtype: "Data", fieldname: "ordered", label: __("Ordered"), read_only: 1, in_list_view: 1, columns: 2 },
					{ fieldtype: "Percent", fieldname: "billed", label: __("Billed So Far"), read_only: 1, in_list_view: 1, columns: 2 },
					{ fieldtype: "Percent", fieldname: "done", label: __("Done"), in_list_view: 1, columns: 2 },
				],
			},
		],
		primary_action_label: __("Create"),
		primary_action: ({ done, by_line, lines }) => {
			dialog.hide();
			frappe.model.open_mapped_doc({
				method: "onedesk.one_project.progress.bill_progress",
				source_name: frm.doc.name,
				args: by_line ? { doctype: frm.doctype, lines: Object.fromEntries((lines || []).map((one) => [one.line, one.done || 0])) } : { doctype: frm.doctype, done },
			});
		},
	});
	dialog.show();
};
