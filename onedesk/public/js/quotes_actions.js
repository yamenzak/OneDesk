frappe.provide("onedesk.quotes");

onedesk.quotes.ask = async (done, { project } = {}) => {
	const mine = project
		? [...new Set((await frappe.db.get_list("Material Request", { filters: [["Material Request Item", "project", "=", project]], fields: ["name"], limit: 0 })).map((one) => one.name))]
		: null;
	const dialog = new frappe.ui.Dialog({
		title: __("Ask for Prices"),
		fields: [
			{
				fieldtype: "Link",
				fieldname: "request",
				label: __("Material Request"),
				options: "Material Request",
				reqd: 1,
				filter_description: mine ? __("The project's requests still to order") : null,
				get_query: () => ({
					filters: [
						["Material Request", "docstatus", "=", 1],
						["Material Request", "material_request_type", "=", "Purchase"],
						["Material Request", "status", "in", ["Pending", "Partially Ordered"]],
						...(mine ? [["Material Request", "name", "in", mine.length ? mine : [""]]] : []),
					],
				}),
			},
			{
				fieldtype: "MultiSelectList",
				fieldname: "suppliers",
				label: __("Suppliers"),
				reqd: 1,
				get_data: (text) => frappe.db.get_link_options("Supplier", text, { disabled: 0 }),
			},
			{ fieldtype: "Small Text", fieldname: "message", label: __("Message"), description: __("Left empty, the usual message is sent.") },
			{ fieldtype: "Check", fieldname: "send", label: __("Email Suppliers Now"), default: 1 },
		],
		primary_action_label: __("Ask"),
		primary_action: async (values) => {
			const made = await frappe.xcall("onedesk.one_inventory.quotes.ask", {
				request: values.request,
				suppliers: values.suppliers,
				message: values.message || null,
				send: values.send ? 1 : 0,
			});
			dialog.hide();
			if (values.send) {
				frappe.show_alert({ message: __("Asked {0} for prices", [frappe.utils.comma_and(values.suppliers)]), indicator: "green" });
				done?.();
			} else {
				frappe.set_route("Form", "Request for Quotation", made);
			}
		},
	});
	dialog.show();
};

onedesk.quotes.add = async (request, supplier) => {
	const quote = await frappe.xcall(
		"erpnext.buying.doctype.request_for_quotation.mapper.make_supplier_quotation_from_rfq",
		{ source_name: request, for_supplier: supplier },
		"GET"
	);
	frappe.model.sync(quote);
	frappe.set_route("Form", quote.doctype, quote.name);
};

onedesk.quotes.order = (quote) =>
	frappe.model.open_mapped_doc({
		method: "erpnext.buying.doctype.supplier_quotation.mapper.make_purchase_order",
		source_name: quote,
	});

onedesk.quotes.order_cheapest = (request, done) =>
	frappe.confirm(__("Draft an order to each supplier for the lines they are cheapest on?"), async () => {
		const made = await frappe.xcall("onedesk.one_inventory.quotes.order_cheapest", { request });
		if (made.length === 1) return frappe.set_route("Form", "Purchase Order", made[0]);
		frappe.show_alert({ message: __("{0} draft orders made", [made.length]), indicator: "green" });
		done?.();
	});
