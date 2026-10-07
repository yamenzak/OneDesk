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
		onedesk.quotation.terms(frm);
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

// A quotation for a project starts with the project's payment terms and terms
// and conditions, once the customer's own have been fetched, as saving it would
// give it (one_project/terms.py `carried`).
onedesk.quotation.terms = (frm) => {
	if (!frm.doc.project || frm.one_terms_given) return;
	frm.one_terms_given = true;
	frappe.after_ajax(async () => {
		const { message } = await frappe.db.get_value("Project", frm.doc.project, ["one_payment_terms", "one_terms"]);
		if (!message || !frm.is_new()) return;
		if (message.one_payment_terms && frm.doc.payment_terms_template !== message.one_payment_terms)
			await frm.set_value("payment_terms_template", message.one_payment_terms);
		if (message.one_terms && !frm.doc.tc_name) await frm.set_value("tc_name", message.one_terms);
	});
};
