frappe.ui.form.on("Mail Rule", {
	setup(frm) {
		frm.set_query("move_to", () => ({ filters: { account: frm.doc.account, hidden: 0 } }));
	},
});
