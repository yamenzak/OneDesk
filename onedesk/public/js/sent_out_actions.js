frappe.provide("onedesk.sent_out");

onedesk.sent_out.new = () => frappe.new_doc("Purchase Order", { is_subcontracted: 1 });

onedesk.sent_out.make_order = (purchase_order) =>
	frappe.model.open_mapped_doc({
		method: "erpnext.buying.doctype.purchase_order.mapper.make_subcontracting_order",
		source_name: purchase_order,
	});

onedesk.sent_out.send = async (order) => {
	const entry = await frappe.xcall("erpnext.controllers.subcontracting_controller.make_rm_stock_entry", {
		subcontract_order: order,
		order_doctype: "Subcontracting Order",
	});
	const synced = frappe.model.sync(entry);
	frappe.set_route("Form", synced[0].doctype, synced[0].name);
};

onedesk.sent_out.receive = (order) =>
	frappe.model.open_mapped_doc({
		method: "erpnext.subcontracting.doctype.subcontracting_order.subcontracting_order.make_subcontracting_receipt",
		source_name: order,
	});
