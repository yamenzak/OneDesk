frappe.ui.form.on("Record Type", {
	refresh(frm) {
		if (frm.doc.record_doctype) frappe.set_route("List", frm.doc.record_doctype);
	},
});
