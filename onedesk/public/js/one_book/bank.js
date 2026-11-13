
onedesk.bank = {
	async ours(company) {
		const found = await frappe.db.get_list("Bank Account", {
			filters: { is_company_account: 1, disabled: 0, ...(company ? { company } : {}) },
			fields: ["name", "is_default"],
			limit: 20,
		});
		const fallback = found.length === 1 ? found[0] : null;
		return (found.find((one) => one.is_default) || fallback || {}).name || null;
	},
	async start(frm) {
		const asked = frappe.route_options && frappe.route_options.bank_account;
		if (asked) frappe.route_options = null;
		if (frm.doc.bank_account && !asked) return;
		const account = asked || (await onedesk.bank.ours(frm.doc.company));
		if (account && account !== frm.doc.bank_account) frm.set_value("bank_account", account);
	},
};

frappe.ui.form.on("Bank Reconciliation Tool", {
	onload(frm) {
		onedesk.bank.start(frm);
	},
	refresh(frm) {
		frm.set_intro();
	},
});

frappe.ui.form.on("Bank Statement Import", {
	onload(frm) {
		if (frm.is_new()) onedesk.bank.start(frm);
	},
});
