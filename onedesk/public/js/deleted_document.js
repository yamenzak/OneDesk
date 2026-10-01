// The Recycle Bin's record (one/recycle.py): frappe's own Restore is its System
// Manager's, so the button puts it back through One's, which a workspace may use.
frappe.ui.form.on("Deleted Document", {
	refresh(frm) {
		frm.remove_custom_button(__("Restore"));
		if (frm.doc.restored) return;
		frm.add_custom_button(__("Restore"), async () => {
			const name = await frappe.xcall("onedesk.one.recycle.restore", { name: frm.doc.name });
			frappe.set_route("Form", frm.doc.deleted_doctype, name);
		}).addClass("btn-primary");
	},
});
