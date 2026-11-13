frappe.ui.form.on("Deleted Document", {
	refresh(frm) {
		frm.remove_custom_button(__("Restore"));
		if (frm.doc.restored) return;
		frm.add_custom_button(__("Restore"), async () => {
			const name = await frappe.xcall("onedesk.one.recycle.restore", { name: frm.doc.name });
			if (frm.doc.deleted_doctype === "Custom Field") {
				frappe.set_route("List", "Workspace Field", { form: name.slice(0, name.lastIndexOf("-")) });
			} else frappe.set_route("Form", frm.doc.deleted_doctype, name);
		});
		frm.change_custom_button_type(__("Restore"), null, "primary");
	},
});
