// A supplier's Items tab (one_inventory/supplier_items.py): what is bought
// from them, item by item, drawn by the onedesk.supplier_items island. It is
// mounted on each refresh of a saved supplier, so the tab says how many items
// before it is opened, and told when the form moves to another supplier.
onedesk.record_tabs.register("items", {
	refresh(frm, field) {
		if (!field) return;
		const props = { supplier: frm.doc.name, onCount: (n) => onedesk.record_tabs.count(frm, "items", n) };
		if (field.one_island) return field.one_island.update(props);
		field.$wrapper.empty();
		field.one_island = frappe.ui.mount_island("onedesk.supplier_items", field.$wrapper[0], props);
	},
});
