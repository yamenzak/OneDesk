// A quotation for a project is to that project's customer, and one for extra
// work becomes a sub-project when it's ordered. See one_project/billing.py.
// One made from a deal, or from the list, offers the customer's open projects,
// and names the one waiting for its quote (one_project/view.py `to_quote`).
frappe.ui.form.on("Quotation", {
	setup(frm) {
		frm.set_query("project", () =>
			frm.doc.quotation_to === "Customer" && frm.doc.party_name
				? { filters: { customer: frm.doc.party_name, status: "Open" } }
				: {}
		);
	},
	refresh(frm) {
		if (!frm.is_new()) return;
		onedesk.quotation.customer(frm);
		onedesk.quotation.project(frm);
	},
	project(frm) {
		onedesk.quotation.customer(frm);
	},
	party_name(frm) {
		onedesk.quotation.project(frm);
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

onedesk.quotation.project = async (frm) => {
	if (!frm.is_new() || frm.doc.project || frm.doc.quotation_to !== "Customer" || !frm.doc.party_name) return;
	const project = await frappe.xcall("onedesk.one_project.view.to_quote", { customer: frm.doc.party_name });
	if (project && !frm.doc.project) frm.set_value("project", project);
};
