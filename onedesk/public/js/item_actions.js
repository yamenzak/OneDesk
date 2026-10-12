// What can be done to an item from its page (one_inventory/page/item_view)
// that the page doesn't do in place: every other field of the item, in
// frappe's own controls, grouped, with its tables, and any field a workspace
// adds under More (onedesk.project.about_fields). Saved against the item as
// the page loaded it, as a form saves. And the documents an item is the start
// of, opened in desk's own form with the item on their first line.
frappe.provide("onedesk.item");

onedesk.item.GROUPS = [
	[__("Details"), ["item_group", "brand", "stock_uom", "one_measured_by", "is_stock_item", "allow_alternative_item", "barcodes"]],
	[__("Stock"), ["valuation_method", "valuation_rate", "allow_negative_stock", "shelf_life_in_days", "end_of_life", "warranty_period", "weight_per_unit", "weight_uom"]],
	[__("Reordering"), ["reorder_levels", "default_material_request_type", "safety_stock", "lead_time_days", "min_order_qty"]],
	[__("Units"), ["uoms", "purchase_uom", "sales_uom"]],
	[__("Serial Numbers and Batches"), ["has_serial_no", "serial_no_series", "use_serial_no_wise_valuation", "has_batch_no", "create_new_batch", "batch_number_series", "has_expiry_date", "retain_sample", "sample_quantity"]],
	[__("Variants"), ["has_variants", "variant_based_on"]],
	[__("Buying"), ["is_purchase_item", "is_customer_provided_item", "delivered_by_supplier", "supplier_items", "over_delivery_receipt_allowance", "country_of_origin", "customs_tariff_number", "purchase_tax_withholding_category", "enable_deferred_expense", "no_of_months_exp"]],
	[__("Selling"), ["is_sales_item", "standard_rate", "max_discount", "over_billing_allowance", "grant_commission", "customer_items", "sales_tax_withholding_category", "enable_deferred_revenue", "no_of_months"]],
	[__("Making"), ["include_item_in_manufacturing", "is_sub_contracted_item", "production_capacity"]],
	[__("Quality"), ["inspection_required_before_purchase", "inspection_required_before_delivery", "quality_inspection_template"]],
	[__("Equipment"), ["is_fixed_asset", "asset_category", "asset_naming_series", "auto_create_assets", "is_grouped_asset"]],
	[__("Accounts"), ["item_defaults", "taxes"]],
];
// Changed in place on the page: its name, its description, whether it is
// disabled. Its code and series are how it was named. Which companies it is
// for is not asked: a workspace is one company.
onedesk.item.ELSEWHERE = ["item_name", "description", "disabled", "item_code", "naming_series", "restrict_to_companies", "allowed_companies"];

onedesk.item.edit = async (item, modified, done, fieldnames = null) => {
	await frappe.model.with_doctype("Item");
	const doc = await frappe.db.get_doc("Item", item);
	const groups = fieldnames || onedesk.project.about_fields("Item", onedesk.item.GROUPS, onedesk.item.ELSEWHERE);
	const fields = groups
		.flatMap((one) => (Array.isArray(one) ? [{ fieldtype: "Section Break", label: one[0], collapsible: !fieldnames && one !== groups[0] }, ...one[1]] : [one]))
		.map((fieldname) => (typeof fieldname === "string" ? onedesk.item.field(doc, fieldname) : fieldname))
		.filter(Boolean);
	const dialog = new frappe.ui.Dialog({
		title: fieldnames ? __("Edit {0}", [__(frappe.meta.get_label("Item", [fieldnames[0]].flat().pop()))]) : __("Edit Details"),
		size: "extra-large",
		fields,
		primary_action_label: __("Save"),
		primary_action: async (values) => {
			dialog.disable_primary_action();
			try {
				const changed = { ...doc, ...values, modified };
				for (const df of fields.filter((one) => one.fieldtype === "Table")) {
					if (df.fieldname in values) changed[df.fieldname] = (values[df.fieldname] || []).filter((row) => Object.keys(row).some((key) => row[key] && !["name", "idx", "doctype"].includes(key)));
				}
				await frappe.xcall("frappe.client.save", { doc: changed });
				dialog.hide();
				done?.();
			} catch {
				// frappe has said why, as a changed item's "Please refresh".
			} finally {
				dialog.enable_primary_action();
			}
		},
	});
	dialog.show();
};

// One of the item's fields as the dialog asks for it. A table is its rows in
// frappe's grid, its columns those the item's form shows, and a row's company
// is the workspace's own.
onedesk.item.field = (doc, fieldname) => {
	const df = frappe.meta.get_docfield("Item", fieldname);
	if (!df) return null;
	if (df.fieldtype !== "Table") return { ...df, default: doc[fieldname] };
	const company = frappe.defaults.get_default("company");
	const columns = frappe.meta
		.get_docfields(df.options)
		.filter((one) => !frappe.model.no_value_type.includes(one.fieldtype) && !one.hidden)
		.map((one) => (one.fieldname === "company" ? { ...one, hidden: 1, in_list_view: 0, default: company } : { ...one }));
	return {
		fieldtype: "Table",
		fieldname,
		label: __(df.label),
		in_place_edit: false,
		data: (doc[fieldname] || []).map((row) => ({ ...row })),
		fields: columns,
	};
};

// A document started from the item, open in desk's form with the item on its
// first line, as the form's Create menu starts one: its own triggers then
// fill the line's price, unit and warehouse.
onedesk.item.start = (doctype, item, values = {}, line = {}, table = "items", field = "item_code") => {
	frappe.model.with_doctype(doctype, () => {
		const doc = frappe.model.get_new_doc(doctype);
		Object.assign(doc, values);
		const row = frappe.model.add_child(doc, table);
		Object.assign(row, { [field]: item, ...line });
		const ready = (_event, frm) => {
			if (!frm || frm.doc.name !== doc.name) return;
			$(document).off("form-refresh", ready);
			frm.script_manager.trigger(field, row.doctype, row.name);
		};
		$(document).on("form-refresh", ready);
		frappe.set_route("Form", doctype, doc.name);
	});
};

// What the item page's head starts, each a document of ERPNext's own.
onedesk.item.order = (item) => onedesk.item.start("Purchase Order", item);
onedesk.item.request = (item) => onedesk.item.start("Material Request", item, { material_request_type: "Purchase" });
onedesk.item.move = (item) => onedesk.item.start("Stock Entry", item, { stock_entry_type: "Material Transfer", purpose: "Material Transfer" });
onedesk.item.count = (item, opening) => onedesk.item.start("Stock Reconciliation", item, opening ? { purpose: "Opening Stock" } : {});
onedesk.item.make = (item, bom) => {
	frappe.model.with_doctype("Work Order", () => {
		const doc = frappe.model.get_new_doc("Work Order");
		Object.assign(doc, { production_item: item, bom_no: bom || undefined });
		const ready = (_event, frm) => {
			if (!frm || frm.doc.name !== doc.name) return;
			$(document).off("form-refresh", ready);
			frm.trigger("production_item");
		};
		$(document).on("form-refresh", ready);
		frappe.set_route("Form", "Work Order", doc.name);
	});
};
onedesk.item.bom = (item) => frappe.new_doc("BOM", { item });
onedesk.item.price = (item, buying) => frappe.new_doc("Item Price", { item_code: item, price_list: frappe.defaults.get_default(buying ? "buying_price_list" : "selling_price_list") || undefined });

// A variant of a template made from its attributes, as ERPNext's Single
// Variant asks for one: a value for each attribute, then the new item in its
// form to name and save.
onedesk.item.variant = async (item) => {
	await frappe.model.with_doctype("Item");
	const doc = await frappe.db.get_doc("Item", item);
	if (doc.variant_based_on !== "Item Attribute") {
		frappe.set_route("Form", "Item", item, { edit: 1 });
		return;
	}
	const fields = [];
	for (const row of doc.attributes || []) {
		const values = row.numeric_values ? [] : await frappe.xcall("frappe.client.get_list", { doctype: "Item Attribute Value", parent: "Item Attribute", filters: { parent: row.attribute }, fields: ["attribute_value"], order_by: "idx asc", limit_page_length: 0 });
		fields.push(
			row.numeric_values
				? { fieldtype: "Float", fieldname: row.attribute, label: __(row.attribute), reqd: 1, description: __("From {0} to {1}, in steps of {2}", [row.from_range, row.to_range, row.increment]) }
				: { fieldtype: "Select", fieldname: row.attribute, label: __(row.attribute), reqd: 1, options: ["", ...values.map((one) => one.attribute_value)] },
		);
	}
	const dialog = new frappe.ui.Dialog({
		title: __("Add Variant"),
		fields,
		primary_action_label: __("Add Variant"),
		primary_action: async (args) => {
			const found = await frappe.xcall("erpnext.controllers.item_variant.get_variant", { template: item, args });
			if (found?.length) {
				dialog.hide();
				frappe.msgprint(__("{0} is already this variant.", [found[0]]));
				return;
			}
			const variant = await frappe.xcall("erpnext.controllers.item_variant.create_variant", { item, args });
			dialog.hide();
			frappe.model.sync(variant);
			frappe.set_route("Form", "Item", variant.name);
		},
	});
	dialog.show();
};

// What Stock on Hand starts, for a warehouse when one is chosen.
frappe.provide("onedesk.stock");
onedesk.stock.move = (warehouse) =>
	frappe.new_doc("Stock Entry", { stock_entry_type: "Material Transfer", purpose: "Material Transfer", from_warehouse: warehouse });
onedesk.stock.count = (warehouse) => frappe.new_doc("Stock Reconciliation", { set_warehouse: warehouse });
onedesk.stock.warehouse = () => frappe.new_doc("Warehouse");
