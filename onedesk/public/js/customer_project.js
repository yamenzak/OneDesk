// A new order, delivery or invoice for a customer with one open project
// names it. See one_project/chain.py `customer_project`.
["Sales Order", "Delivery Note", "Sales Invoice"].forEach((doctype) => {
	frappe.ui.form.on(doctype, {
		async customer(frm) {
			if (!frm.is_new() || frm.doc.project || !frm.doc.customer) return;
			const project = await frappe.xcall("onedesk.one_project.chain.customer_project", { customer: frm.doc.customer });
			if (project && !frm.doc.project) frm.set_value("project", project);
		},
	});
});
