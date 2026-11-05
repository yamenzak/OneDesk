frappe.provide("onedesk.supplier_items");

onedesk.supplier_items.adopt = () => {
	const Party = erpnext.PartyItems;
	if (!Party || Party.prototype.one_supplier_items) return;
	Party.prototype.one_supplier_items = true;
	const theirs = Party.prototype.make_frequent_list;
	Party.prototype.make_frequent_list = function () {
		if (this.frm.doctype !== "Supplier") return theirs.call(this);
		const field = this.frm.fields_dict.frequently_bought_html;
		if (!field) return;
		const props = { supplier: this.frm.doc.name };
		if (field.one_island) return field.one_island.update(props);
		field.$wrapper.empty();
		field.one_island = frappe.ui.mount_island("onedesk.supplier_items", field.$wrapper[0], props);
	};
};

frappe.ui.form.on("Supplier", {
	setup() {
		onedesk.supplier_items.adopt();
	},
});
