// A quotation for extra work on a project is to that project's customer. See
// one_project/billing.py.
frappe.ui.form.on("Quotation", {
	refresh(frm) {
		if (frm.is_new()) onedesk.quotation.customer(frm);
	},
	one_project(frm) {
		onedesk.quotation.customer(frm);
	},
});

frappe.provide("onedesk.quotation");

onedesk.quotation.customer = async (frm) => {
	if (!frm.doc.one_project || frm.doc.party_name) return;
	const { message } = await frappe.db.get_value("Project", frm.doc.one_project, "customer");
	const customer = message && message.customer;
	if (!customer) return;
	await frm.set_value("quotation_to", "Customer");
	frm.set_value("party_name", customer);
};
