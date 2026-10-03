// A collection has no page of its own: opening one opens its records.
frappe.ui.form.on("Record Type", {
	refresh(frm) {
		if (frm.doc.record_doctype) frappe.set_route("List", frm.doc.record_doctype);
	},
});
