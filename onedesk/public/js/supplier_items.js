onedesk.record_tabs.register("items", {
	refresh(frm, field) {
		if (!field) return;
		const props = { supplier: frm.doc.name, onCount: (n) => onedesk.record_tabs.count(frm, "items", n) };
		if (field.one_island) return field.one_island.update(props);
		field.$wrapper.empty();
		field.one_island = frappe.ui.mount_island("onedesk.supplier_items", field.$wrapper[0], props);
	},
});
