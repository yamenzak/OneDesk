// What the Sent Out page (one_inventory/page/sent_out) does, each through
// ERPNext's own calls, as the Subcontracting Order's own form makes them.
frappe.provide("onedesk.sent_out");

// Work to send out starts as a purchase order for the supplier's service,
// marked as subcontracted.
onedesk.sent_out.new = () => frappe.new_doc("Purchase Order", { is_subcontracted: 1 });

// The subcontracting order a subcontracted purchase order needs before
// anything can go out.
onedesk.sent_out.make_order = (purchase_order) =>
	frappe.model.open_mapped_doc({
		method: "erpnext.buying.doctype.purchase_order.mapper.make_subcontracting_order",
		source_name: purchase_order,
	});

// The materials to the supplier: ERPNext's transfer, opened as a draft.
onedesk.sent_out.send = async (order) => {
	const entry = await frappe.xcall("erpnext.controllers.subcontracting_controller.make_rm_stock_entry", {
		subcontract_order: order,
		order_doctype: "Subcontracting Order",
	});
	const synced = frappe.model.sync(entry);
	frappe.set_route("Form", synced[0].doctype, synced[0].name);
};

// What the supplier made, taken back into the stores: ERPNext's receipt,
// opened as a draft.
onedesk.sent_out.receive = (order) =>
	frappe.model.open_mapped_doc({
		method: "erpnext.subcontracting.doctype.subcontracting_order.subcontracting_order.make_subcontracting_receipt",
		source_name: order,
	});
