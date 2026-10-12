// What the Plant Floor (one_inventory/page/plant) does, each through
// ERPNext's own calls, asked in frappe's own dialogs as ERPNext's Plant Floor
// asks them (manufacturing/doctype/plant_floor). `done` reads the page again.
frappe.provide("onedesk.plant");

// A workstation's status, saved on the workstation, which tells every open
// Plant Floor (ERPNext's Workstation.on_update).
onedesk.plant.status = (workstation, now, statuses, done) => {
	frappe.prompt(
		[
			{
				fieldtype: "Select",
				fieldname: "status",
				label: __("Status"),
				options: statuses.map((value) => ({ value, label: __(value) })),
				default: now,
				reqd: 1,
			},
		],
		async (values) => {
			await frappe.xcall("frappe.client.set_value", { doctype: "Workstation", name: workstation, fieldname: "status", value: values.status });
			done?.();
		},
		__("Change Status of {0}", [workstation]),
		__("Save")
	);
};

// Stock brought onto the floor, or moved off it to another warehouse, made by
// the Plant Floor's own make_stock_entry and opened as a draft to check.
onedesk.plant.stock = (plant, item, purpose) => {
	const moving = purpose === "Material Transfer";
	frappe.prompt(
		[
			{ fieldtype: "Data", fieldname: "item", label: __("Item"), default: item.item_name, read_only: 1 },
			{ fieldtype: "Float", fieldname: "qty", label: __("Quantity"), reqd: 1 },
			...(moving
				? [
						{
							fieldtype: "Link",
							fieldname: "to_warehouse",
							label: __("To Warehouse"),
							options: "Warehouse",
							reqd: 1,
							get_query: () => ({ filters: { is_group: 0 } }),
						},
					]
				: []),
		],
		async (values) => {
			if (!(flt(values.qty) > 0)) return frappe.msgprint(__("Quantity must be greater than zero."));
			const doc = await frappe.xcall("run_doc_method", {
				dt: "Plant Floor",
				dn: plant.name,
				method: "make_stock_entry",
				args: JSON.stringify({
					kwargs: {
						company: plant.company,
						item_code: item.item_code,
						qty: flt(values.qty),
						from_warehouse: moving ? plant.warehouse : "",
						to_warehouse: moving ? values.to_warehouse : plant.warehouse,
						purpose,
					},
				}),
			});
			const [made] = frappe.model.sync(doc);
			frappe.set_route("Form", made.doctype, made.name);
		},
		moving ? __("Move Stock") : __("Add Stock"),
		__("Create")
	);
};
