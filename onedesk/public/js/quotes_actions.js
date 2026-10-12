// What the Quotes page (one_inventory/page/quotes) does, each through
// ERPNext's own mappers, asked in frappe's own dialogs. `done` reads the page
// again.
frappe.provide("onedesk.quotes");

// Asking suppliers to price what a material request still needs. Sent now,
// the request is submitted and each supplier mailed a link, as its form's
// Send Email does. Otherwise it opens as a draft.
onedesk.quotes.ask = (done) => {
	const dialog = new frappe.ui.Dialog({
		title: __("Ask for Prices"),
		fields: [
			{
				fieldtype: "Link",
				fieldname: "request",
				label: __("Material Request"),
				options: "Material Request",
				reqd: 1,
				get_query: () => ({
					filters: { docstatus: 1, material_request_type: "Purchase", status: ["in", ["Pending", "Partially Ordered"]] },
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
			{ fieldtype: "Check", fieldname: "send", label: __("Mail the Suppliers Now"), default: 1 },
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

// A supplier's quote, typed in from their mail: ERPNext's own quote from the
// request, opened as a draft with their name on it.
// It is called as the request's own form calls it.
onedesk.quotes.add = async (request, supplier) => {
	const quote = await frappe.xcall(
		"erpnext.buying.doctype.request_for_quotation.mapper.make_supplier_quotation_from_rfq",
		{ source_name: request, for_supplier: supplier },
		"GET"
	);
	frappe.model.sync(quote);
	frappe.set_route("Form", quote.doctype, quote.name);
};

// An order from one supplier's quote, opened as a draft.
onedesk.quotes.order = (quote) =>
	frappe.model.open_mapped_doc({
		method: "erpnext.buying.doctype.supplier_quotation.mapper.make_purchase_order",
		source_name: quote,
	});

// A draft order to each supplier for the lines they are cheapest on.
onedesk.quotes.order_cheapest = (request, done) =>
	frappe.confirm(__("Draft an order to each supplier for the lines they are cheapest on?"), async () => {
		const made = await frappe.xcall("onedesk.one_inventory.quotes.order_cheapest", { request });
		if (made.length === 1) return frappe.set_route("Form", "Purchase Order", made[0]);
		frappe.show_alert({ message: __("{0} draft orders made", [made.length]), indicator: "green" });
		done?.();
	});
