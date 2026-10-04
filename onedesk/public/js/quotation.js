// A quotation for a project is to that project's customer, and one for extra
// work becomes a sub-project when it's ordered. See one_project/billing.py.
frappe.ui.form.on("Quotation", {
	refresh(frm) {
		if (frm.is_new()) onedesk.quotation.customer(frm);
	},
	project(frm) {
		onedesk.quotation.customer(frm);
	},
});

frappe.provide("onedesk.quotation");

onedesk.quotation.customer = async (frm) => {
	if (!frm.doc.project || frm.doc.party_name) return;
	const { message } = await frappe.db.get_value("Project", frm.doc.project, "customer");
	const customer = message && message.customer;
	if (!customer) return;
	await frm.set_value("quotation_to", "Customer");
	frm.set_value("party_name", customer);
};
