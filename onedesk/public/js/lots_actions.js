frappe.provide("onedesk.lots");

onedesk.lots.track = (item, done) => {
	const dialog = new frappe.ui.Dialog({
		title: __("Track Batches"),
		fields: [
			{
				fieldtype: "Link",
				fieldname: "item",
				label: __("Item"),
				options: "Item",
				default: item || "",
				reqd: 1,
				read_only: item ? 1 : 0,
				get_query: () => ({ query: "onedesk.one_inventory.lots.can_be_tracked" }),
			},
			{
				fieldtype: "Select",
				fieldname: "kind",
				label: __("Keep It"),
				options: [
					{ value: "lots", label: __("In batches, each with its dates") },
					{ value: "serials", label: __("By Serial No, piece by piece") },
				],
				default: "lots",
				reqd: 1,
			},
			{ fieldtype: "Section Break", depends_on: "eval:doc.kind=='lots'" },
			{ fieldtype: "Check", fieldname: "auto", label: __("Automatically Create New Batch"), default: 1 },
			{
				fieldtype: "Data",
				fieldname: "batch_series",
				label: __("Batch Number Series"),
				description: __("For example LOT-.YYYY.-.####"),
				depends_on: "eval:doc.auto",
			},
			{ fieldtype: "Check", fieldname: "expires", label: __("Has Expiry Date"), default: 0 },
			{
				fieldtype: "Int",
				fieldname: "shelf_life",
				label: __("Shelf Life In Days"),
				depends_on: "eval:doc.expires",
			},
			{ fieldtype: "Section Break", depends_on: "eval:doc.kind=='serials'" },
			{
				fieldtype: "Data",
				fieldname: "serial_series",
				label: __("Serial Number Series"),
				description: __("For example SN-.#####. Left empty, each number is typed in."),
			},
			{ fieldtype: "Int", fieldname: "warranty", label: __("Warranty Period (in days)") },
		],
		primary_action_label: __("Save"),
		primary_action: async (values) => {
			const lots = values.kind === "lots";
			const fields = lots
				? {
						has_batch_no: 1,
						create_new_batch: values.auto ? 1 : 0,
						batch_number_series: values.auto ? values.batch_series || "" : "",
						has_expiry_date: values.expires ? 1 : 0,
						shelf_life_in_days: values.expires ? cint(values.shelf_life) : 0,
					}
				: { has_serial_no: 1, serial_no_series: values.serial_series || "", warranty_period: cint(values.warranty) || 0 };
			await frappe.xcall("frappe.client.set_value", { doctype: "Item", name: values.item, fieldname: fields });
			dialog.hide();
			frappe.show_alert({ message: lots ? __("{0} is kept in batches", [values.item]) : __("{0} is kept by Serial No", [values.item]), indicator: "green" });
			done?.();
		},
	});
	dialog.show();
};

onedesk.lots.new_lot = async (item, done) => {
	const auto = item ? await frappe.db.get_value("Item", item, ["create_new_batch", "has_expiry_date"]) : null;
	const own = auto?.message || {};
	const dialog = new frappe.ui.Dialog({
		title: __("New Batch"),
		fields: [
			{
				fieldtype: "Link",
				fieldname: "item",
				label: __("Item"),
				options: "Item",
				default: item || "",
				reqd: 1,
				read_only: item ? 1 : 0,
				get_query: () => ({ filters: { has_batch_no: 1, disabled: 0 } }),
			},
			{
				fieldtype: "Data",
				fieldname: "batch_id",
				label: __("Batch ID"),
				reqd: item && own.create_new_batch ? 0 : 1,
				description: item && own.create_new_batch ? __("Left empty, the next number is given.") : "",
			},
			{ fieldtype: "Date", fieldname: "manufacturing_date", label: __("Manufacturing Date"), default: frappe.datetime.get_today() },
			{
				fieldtype: "Date",
				fieldname: "expiry_date",
				label: __("Expiry Date"),
				description: __("Left empty, worked out from how long the item keeps."),
			},
			{ fieldtype: "Link", fieldname: "supplier", label: __("Supplier"), options: "Supplier" },
		],
		primary_action_label: __("Create"),
		primary_action: async (values) => {
			const made = await frappe.xcall("frappe.client.insert", {
				doc: {
					doctype: "Batch",
					item: values.item,
					batch_id: values.batch_id || "",
					manufacturing_date: values.manufacturing_date,
					expiry_date: values.expiry_date || null,
					supplier: values.supplier || null,
				},
			});
			dialog.hide();
			frappe.show_alert({ message: __("Batch {0} made", [made.batch_id || made.name]), indicator: "green" });
			done?.();
		},
	});
	dialog.show();
};

onedesk.lots.switch_on = (done) =>
	frappe.confirm(__("Let items be kept in batches or by Serial No?"), async () => {
		await frappe.xcall("onedesk.one_inventory.ready.fix", { key: "serials" });
		done?.();
	});
