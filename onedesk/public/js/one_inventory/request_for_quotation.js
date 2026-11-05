frappe.ui.form.on("Request for Quotation", {
	async refresh(frm) {
		if (frm.doc.docstatus !== 1 || !frappe.model.can_create("Purchase Order")) return;
		const quoted = await frappe.db.get_list("Supplier Quotation", {
			filters: [
				["Supplier Quotation Item", "request_for_quotation", "=", frm.doc.name],
				["docstatus", "=", 1],
			],
			limit: 1,
		});
		if (!quoted.length) return;
		frm.add_custom_button(
			__("Order Cheapest"),
			() => frappe.require("/assets/onedesk/js/quotes_actions.js").then(() => onedesk.quotes.order_cheapest(frm.doc.name, () => frm.reload_doc())),
			__("Create")
		);
	},
});
