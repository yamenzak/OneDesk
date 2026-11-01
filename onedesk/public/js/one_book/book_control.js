// OneBook's settings (docs/READY.md, mechanism 5): what every module's finds,
// its lists, roles and notifications (module_settings.centers).
frappe.provide("onedesk.book");
onedesk.book.settings = ({ at = null } = {}) => {
	const dialog = onedesk.module_settings.open({ module: "OneBook", tabs: [], default_tab: at });
	dialog.show();
	return dialog;
};

frappe.provide("onedesk.control_centers");
onedesk.control_centers.OneBook = onedesk.book.settings;

// Its foot: Settings, the tour, Help and the version at the foot of its rail,
// drawn by the window under whichever of its screens is open (module_foot).
$(document).on("page-change", () =>
	setTimeout(() => {
		const sidebar = frappe.app && frappe.app.sidebar;
		const win = onedesk.interface.current();
		if (!win || win.$foot_action || !sidebar || sidebar.current_module !== "OneBook") return;
		win.module_foot({ module: "OneBook", settings: () => onedesk.book.settings() });
		onedesk.interface.nav.place();
	}, 0)
);

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
