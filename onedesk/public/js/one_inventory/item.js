frappe.provide("onedesk.item");

onedesk.item.PARTS = { one_stock_part: "stock", one_buying_part: "buying", one_selling_part: "selling", one_making_part: "making" };

onedesk.item.parts = (frm) => {
	for (const [fieldname, part] of Object.entries(onedesk.item.PARTS)) {
		const field = frm.fields_dict[fieldname];
		if (!field) continue;
		const props = { item: frm.doc.name, part, frm };
		if (field.one_island) {
			field.one_island.update(props);
			continue;
		}
		field.$wrapper.empty();
		field.one_island = frappe.ui.mount_island("onedesk.item_part", field.$wrapper[0], props);
	}
};

onedesk.item.verbs = async (frm) => {
	await frappe.require(["/assets/onedesk/js/project_actions.js", "/assets/onedesk/js/item_actions.js", "/assets/onedesk/js/lots_actions.js"]);
	const doc = frm.doc;
	const usable = !doc.disabled && !doc.has_variants;
	const can = (doctype) => frappe.model.can_create(doctype);
	const made = doc.default_bom;
	if (usable && made && can("Work Order")) frm.add_custom_button(__("Make More"), () => onedesk.item.make(doc.name, made));
	else if (usable && doc.is_purchase_item && can("Purchase Order")) frm.add_custom_button(__("Order More"), () => onedesk.item.order(doc.name));
	if (usable && doc.is_purchase_item && can("Material Request")) frm.add_custom_button(__("Request Material"), () => onedesk.item.request(doc.name), __("Create"));
	if (usable && doc.is_stock_item && can("Stock Entry")) frm.add_custom_button(__("Transfer Stock"), () => onedesk.item.move(doc.name), __("Create"));
	if (usable && doc.is_stock_item && can("Stock Reconciliation")) frm.add_custom_button(__("Count Stock"), () => onedesk.item.count(doc.name, false), __("Create"));
	if (doc.has_variants && can("Item")) frm.add_custom_button(__("Add Variant"), () => onedesk.item.variant(doc.name));
};

frappe.ui.form.on("Item", {
	refresh(frm) {
		frm.toggle_display(Object.keys(onedesk.item.PARTS), !frm.is_new());
		if (frm.is_new()) return;
		onedesk.item.parts(frm);
		onedesk.item.verbs(frm);
	},
});
