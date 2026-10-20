// "Open in a workbook" under every table on a saved record: the table becomes
// the first sheet of a workbook attached to the record (one_sheet/table.py).
frappe.provide("onedesk.table_workbook");

onedesk.table_workbook.open = (frm, field) => {
	if (frm.is_dirty()) {
		frappe.msgprint(__("Save this record first, so the workbook starts from what is saved."));
		return;
	}
	frappe
		.call({
			method: "onedesk.one_sheet.table.open_table",
			args: { doctype: frm.doctype, name: frm.doc.name, field },
			freeze: true,
		})
		.then((r) => r.message && frappe.set_route("workbook", r.message));
};

frappe.ui.form.on("*", {
	refresh(frm) {
		if (frm.is_new() || frm.meta.istable || frm.meta.issingle) return;
		for (const df of frm.meta.fields) {
			const grid = df.fieldtype === "Table" && frm.fields_dict[df.fieldname]?.grid;
			if (!grid || grid.one_workbook) continue;
			grid.one_workbook = grid.add_custom_button(__("Open in a workbook"), () =>
				onedesk.table_workbook.open(frm, df.fieldname)
			);
		}
	},
});
