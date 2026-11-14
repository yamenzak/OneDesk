// OneBook's settings (docs/READY.md, mechanism 5): what every module's finds,
// its lists, roles and notifications (onedesk.centers.found), and Payment
// Approval, when a payment waits for a second person, the reader's company's
// own fields (one_book/control.py).
frappe.provide("onedesk.book");
const BOOK = "onedesk.one_book.control.";

onedesk.centers.part("settings", onedesk.names.of("one_book"), {
	sections: () => [
		{
			group: null,
			items: [
				{
					id: "approval",
					label: __("Payment Approval"),
					icon: "shield-check",
					title: __("Payment Approval"),
					description: __("When a payment waits for a second person to approve it."),
					async fields() {
						const said = await frappe.xcall(BOOK + "approval");
						const field = (fieldname, fieldtype, label, description, extra = {}) => ({
							fieldname,
							fieldtype,
							label,
							description,
							default: said[fieldname],
							read_only: !said.may,
							...extra,
						});
						return [
							field("one_approve_above", "Currency", __("Payment Approval Limit"), __("A payment above this needs a second person's approval, unless set to 0."), {
								options: said.currency,
							}),
							field("one_approve_first_payment", "Check", __("Require Approval of First Payments"), __("If enabled, the first payment to a supplier or customer needs a second person's approval.")),
							field("one_approve_bank_days", "Int", __("Approval After Bank Change (Days)"), __("Number of days after a party's bank details change in which paying them needs approval, unless set to 0.")),
						];
					},
					save: (values) => frappe.xcall(BOOK + "save_approval", values),
				},
			],
		},
	],
});

// The Bank Reconciliation Tool opens on the company's bank account and far
// enough back to hold every line still to match, so what Home counts as
// unreconciled is on screen without pressing anything.
frappe.ui.form.on("Bank Reconciliation Tool", {
	onload(frm) {
		if (frm.doc.bank_account) return;
		frappe
			.xcall("onedesk.one_book.bank.reconciling", { company: frm.doc.company || null })
			.then((said) => {
				if (!said || !said.bank_account || frm.doc.bank_account) return;
				if (said.from_date && said.from_date < frm.doc.bank_statement_from_date) {
					frm.doc.bank_statement_from_date = said.from_date;
				}
				return frm.set_value("bank_account", said.bank_account).then(() => frm.trigger("make_reconciliation_tool"));
			});
	},
});
