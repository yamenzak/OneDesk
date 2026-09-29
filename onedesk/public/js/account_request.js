// A signup, from the operator's side. Where it stands, what that means and
// Build Workspace are its Record Head (one_admin/heads.py); this is the way
// from a request to the workspace it became, and to its payment at Stripe.
frappe.ui.form.on("Account Request", {
	refresh(frm) {
		// Only operators read a signup, so sharing it gives nobody anything.
		frm.sidebar.sidebar.find(".form-shared").addClass("hidden");
		if (frm.is_new()) return;
		if (frm.doc.tenant) {
			frm.add_custom_button(__("Open Workspace"), () => frappe.set_route("Form", "Tenant", frm.doc.tenant));
		}
		const session = frm.doc.stripe_session;
		if (session) {
			// Stripe's own search finds a checkout by its id, in test or live.
			const test = session.startsWith("cs_test_") ? "test/" : "";
			frm.page.add_menu_item(__("Open in Stripe"), () =>
				window.open(`https://dashboard.stripe.com/${test}search?query=${encodeURIComponent(session)}`, "_blank"),
			);
		}
	},
});
