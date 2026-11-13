frappe.ui.form.on("Workspace Server", {
	refresh(frm) {
		const field = frm.fields_dict.metrics;
		if (!field || frm.is_new()) return;
		const props = { server: frm.doc.name };
		if (field.one_island) {
			field.one_island.update(props);
			return;
		}
		field.$wrapper.empty();
		field.one_island = frappe.ui.mount_island("onedesk.oneadmin_server_part", field.$wrapper[0], props);
	},
});
