frappe.provide("onedesk.item");

onedesk.item.GROUPS = [
	[__("Details"), ["item_group", "brand", "stock_uom", "one_measured_by", "one_size_uom", "is_stock_item", "allow_alternative_item", "barcodes"]],
	[__("Stock"), ["valuation_method", "valuation_rate", "allow_negative_stock", "shelf_life_in_days", "end_of_life", "warranty_period", "weight_per_unit", "weight_uom"]],
	[__("Reordering"), ["reorder_levels", "default_material_request_type", "safety_stock", "lead_time_days", "min_order_qty"]],
	[__("Units"), ["uoms", "purchase_uom", "sales_uom"]],
	[__("Serial Nos and Batches"), ["has_serial_no", "serial_no_series", "use_serial_no_wise_valuation", "has_batch_no", "create_new_batch", "batch_number_series", "has_expiry_date", "retain_sample", "sample_quantity"]],
	[__("Variants"), ["has_variants", "variant_based_on"]],
	[__("Buying"), ["is_purchase_item", "is_customer_provided_item", "delivered_by_supplier", "supplier_items", "over_delivery_receipt_allowance", "country_of_origin", "customs_tariff_number", "purchase_tax_withholding_category", "enable_deferred_expense", "no_of_months_exp"]],
	[__("Selling"), ["is_sales_item", "standard_rate", "max_discount", "over_billing_allowance", "grant_commission", "customer_items", "sales_tax_withholding_category", "enable_deferred_revenue", "no_of_months"]],
	[__("Manufacturing"), ["include_item_in_manufacturing", "is_sub_contracted_item", "production_capacity"]],
	[__("Quality"), ["inspection_required_before_purchase", "inspection_required_before_delivery", "quality_inspection_template"]],
	[__("Asset"), ["is_fixed_asset", "asset_category", "asset_naming_series", "auto_create_assets", "is_grouped_asset"]],
	[__("Accounts"), ["item_defaults", "taxes"]],
];
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
			} finally {
				dialog.enable_primary_action();
			}
		},
	});
	dialog.show();
};

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

onedesk.item.start = (doctype, item, values = {}, line = {}, table = "items", field = "item_code") => {
	frappe.model.with_doctype(doctype, () => {
		const doc = frappe.model.get_new_doc(doctype);
		Object.assign(doc, values);
		for (const [fieldname, rows] of Object.entries(values)) {
			if (!Array.isArray(rows)) continue;
			doc[fieldname] = [];
			rows.forEach((one) => Object.assign(frappe.model.add_child(doc, fieldname), one));
		}
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

onedesk.item.order = (item, supplier) => onedesk.item.start("Purchase Order", item, supplier ? { supplier } : {});
onedesk.item.quote = (item, customer) =>
	onedesk.item.start("Quotation", item, customer ? { quotation_to: "Customer", party_name: customer } : {});
onedesk.item.sell = (item, customer) => onedesk.item.start("Sales Order", item, customer ? { customer } : {});
onedesk.item.ask = (item, supplier) =>
	onedesk.item.start("Request for Quotation", item, supplier ? { suppliers: [{ supplier }] } : {});
onedesk.item.mapped = (method, source_name, args, triggers = false) =>
	frappe.model.open_mapped_doc({ method, source_name, args, run_link_triggers: triggers });
onedesk.item.request = (item) => onedesk.item.start("Material Request", item, { material_request_type: "Purchase" });
onedesk.item.move = (item, warehouse) => onedesk.stock.move(warehouse, item);
onedesk.item.count = (item, opening, warehouse) =>
	onedesk.item.start(
		"Stock Reconciliation",
		item,
		{ ...(opening ? { purpose: "Opening Stock" } : {}), ...(warehouse ? { set_warehouse: warehouse } : {}) },
		warehouse ? { warehouse } : {}
	);
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
onedesk.item.manufacturer = (item) => frappe.new_doc("Item Manufacturer", { item_code: item });
onedesk.item.finish = (work_order, most) => {
	frappe.prompt(
		[{ fieldtype: "Float", fieldname: "qty", label: __("How Many Made"), reqd: 1, default: most, description: __("Up to {0}", [most]) }],
		async ({ qty }) => {
			if (!(qty > 0)) {
				frappe.msgprint(__("Quantity must be greater than zero."));
				return;
			}
			const entry = await frappe.xcall("erpnext.manufacturing.doctype.work_order.mapper.make_stock_entry", { work_order_id: work_order, purpose: "Manufacture", qty });
			frappe.model.sync(entry);
			frappe.set_route("Form", entry.doctype, entry.name);
		},
		__("Finish {0}", [work_order]),
		__("Finish")
	);
};
onedesk.item.price = (item, buying) => frappe.new_doc("Item Price", { item_code: item, price_list: frappe.defaults.get_default(buying ? "buying_price_list" : "selling_price_list") || undefined });

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

frappe.provide("onedesk.stock");
onedesk.stock.move = (warehouse, item) => {
	const places = (other) => () => ({ filters: { is_group: 0, disabled: 0, ...(other() ? { name: ["!=", other()] } : {}) } });
	const dialog = new frappe.ui.Dialog({
		title: __("Transfer Stock"),
		size: "large",
		fields: [
			{ fieldtype: "Link", fieldname: "source", label: __("From"), options: "Warehouse", reqd: 1, default: warehouse, get_query: places(() => dialog.get_value("target")) },
			{ fieldtype: "Column Break" },
			{ fieldtype: "Link", fieldname: "target", label: __("To"), options: "Warehouse", reqd: 1, get_query: places(() => dialog.get_value("source")) },
			{ fieldtype: "Section Break" },
			{
				fieldtype: "Table",
				fieldname: "lines",
				label: __("Items"),
				reqd: 1,
				in_place_edit: true,
				data: [{ item: item || "", qty: null }],
				fields: [
					{ fieldtype: "Link", fieldname: "item", label: __("Item"), options: "Item", in_list_view: 1, reqd: 1, columns: 7, get_query: () => ({ filters: { is_stock_item: 1, disabled: 0, has_variants: 0 } }) },
					{ fieldtype: "Float", fieldname: "qty", label: __("Quantity"), in_list_view: 1, reqd: 1, columns: 3 },
				],
			},
			{ fieldtype: "Section Break" },
			{ fieldtype: "Link", fieldname: "project", label: __("Project"), options: "Project", get_query: () => ({ filters: { status: "Open" } }) },
			{ fieldtype: "Column Break" },
			{ fieldtype: "Data", fieldname: "remarks", label: __("Remarks") },
		],
		primary_action_label: __("Transfer Stock"),
		primary_action: async ({ source, target, lines, project, remarks }) => {
			dialog.disable_primary_action();
			try {
				const name = await frappe.xcall("onedesk.one_inventory.stock.transfer", { source, target, lines, project, remarks });
				dialog.hide();
				frappe.show_alert({ message: `${__("Moved to {0}", [frappe.utils.escape_html(target)])} · ${frappe.utils.get_form_link("Stock Entry", name, true)}`, indicator: "green" }, 7);
			} finally {
				dialog.enable_primary_action();
			}
		},
		secondary_action_label: __("Open Full Form"),
		secondary_action: () => {
			const { source, target, project, remarks } = dialog.get_values(true) || {};
			dialog.hide();
			frappe.new_doc("Stock Entry", { stock_entry_type: "Material Transfer", purpose: "Material Transfer", from_warehouse: source, to_warehouse: target, project, remarks });
		},
	});
	dialog.show();
};
onedesk.stock.issue = ({ project, title, warehouse, done } = {}) => {
	if (project && title) frappe.utils.add_link_title("Project", project, title);
	const dialog = new frappe.ui.Dialog({
		title: __("Issue Stock"),
		size: "large",
		fields: [
			{ fieldtype: "Link", fieldname: "source", label: __("From"), options: "Warehouse", reqd: 1, default: warehouse, get_query: () => ({ filters: { is_group: 0, disabled: 0 } }) },
			{ fieldtype: "Column Break" },
			{ fieldtype: "Link", fieldname: "project", label: __("Project"), options: "Project", default: project, read_only: project ? 1 : 0, get_query: () => ({ filters: { status: "Open" } }) },
			{ fieldtype: "Section Break" },
			{
				fieldtype: "Table",
				fieldname: "lines",
				label: __("Items"),
				reqd: 1,
				in_place_edit: true,
				data: [{ item: "", qty: null }],
				fields: [
					...onedesk.stock.lines(),
				],
			},
			{ fieldtype: "Section Break" },
			{ fieldtype: "Data", fieldname: "remarks", label: __("Remarks") },
		],
		primary_action_label: __("Issue Stock"),
		primary_action: async ({ source, lines, project: on, remarks }) => {
			dialog.disable_primary_action();
			try {
				const name = await frappe.xcall("onedesk.one_inventory.stock.issue", { source, lines, project: on, remarks });
				dialog.hide();
				frappe.show_alert({ message: `${__("Issued from {0}", [frappe.utils.escape_html(source)])} · ${frappe.utils.get_form_link("Stock Entry", name, true)}`, indicator: "green" }, 7);
				done?.();
			} finally {
				dialog.enable_primary_action();
			}
		},
		secondary_action_label: __("Open Full Form"),
		secondary_action: () => {
			const { source, project: on, remarks } = dialog.get_values(true) || {};
			dialog.hide();
			frappe.new_doc("Stock Entry", { stock_entry_type: "Material Issue", purpose: "Material Issue", from_warehouse: source, project: on, remarks });
		},
	});
	dialog.show();
};
// An item kept in stock, how many, and the unit it's counted in here: a
// profile kept in metres is issued by the bar, and comes back by the metre.
onedesk.stock.lines = () => [
	{ fieldtype: "Link", fieldname: "item", label: __("Item"), options: "Item", in_list_view: 1, reqd: 1, columns: 5, get_query: () => ({ filters: { is_stock_item: 1, disabled: 0, has_variants: 0 } }) },
	{ fieldtype: "Float", fieldname: "qty", label: __("Quantity"), in_list_view: 1, reqd: 1, columns: 2 },
	{ fieldtype: "Link", fieldname: "uom", label: __("Unit"), options: "UOM", in_list_view: 1, columns: 3, description: __("Empty is the item's own unit.") },
];
onedesk.stock.give_back = ({ project, title, warehouse, done } = {}) => {
	if (project && title) frappe.utils.add_link_title("Project", project, title);
	const dialog = new frappe.ui.Dialog({
		title: __("Return to Store"),
		size: "large",
		fields: [
			{ fieldtype: "Link", fieldname: "project", label: __("From Project"), options: "Project", reqd: 1, default: project, read_only: project ? 1 : 0 },
			{ fieldtype: "Column Break" },
			{ fieldtype: "Link", fieldname: "target", label: __("To"), options: "Warehouse", reqd: 1, default: warehouse, get_query: () => ({ filters: { is_group: 0, disabled: 0 } }) },
			{ fieldtype: "Section Break" },
			{ fieldtype: "Table", fieldname: "lines", label: __("Items"), reqd: 1, in_place_edit: true, data: [{ item: "", qty: null }], fields: onedesk.stock.lines() },
			{ fieldtype: "Section Break" },
			{ fieldtype: "Data", fieldname: "remarks", label: __("Remarks") },
		],
		primary_action_label: __("Return to Store"),
		primary_action: async ({ project: from, target, lines, remarks }) => {
			dialog.disable_primary_action();
			try {
				const name = await frappe.xcall("onedesk.one_project.materials.give_back", { target, lines, project: from, remarks });
				dialog.hide();
				frappe.show_alert({ message: `${__("Back in {0}", [frappe.utils.escape_html(target)])} · ${frappe.utils.get_form_link("Stock Entry", name, true)}`, indicator: "green" }, 7);
				done?.();
			} finally {
				dialog.enable_primary_action();
			}
		},
	});
	dialog.show();
};
onedesk.stock.count = (warehouse) => frappe.new_doc("Stock Reconciliation", { set_warehouse: warehouse });
onedesk.stock.warehouse = () => frappe.new_doc("Warehouse");
