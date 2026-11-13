// OneBook's settings (docs/READY.md, mechanism 5): what every module's finds,
// its lists, roles and notifications (onedesk.centers.found).
frappe.provide("onedesk.book");
onedesk.centers.part("settings", onedesk.names.of("one_book"));

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
