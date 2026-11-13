frappe.ui.form.on("Account Request", {
	refresh(frm) {
		frm.sidebar.sidebar.find(".form-shared").addClass("hidden");
		if (frm.is_new()) return;
		if (frm.doc.tenant) {
			frm.add_custom_button(__("Open Workspace"), () => frappe.set_route("Form", "Tenant", frm.doc.tenant));
		}
		const session = frm.doc.stripe_session;
		if (session) {
			const test = session.startsWith("cs_test_") ? "test/" : "";
			frm.page.add_menu_item(__("Open in Stripe"), () =>
				window.open(`https://dashboard.stripe.com/${test}search?query=${encodeURIComponent(session)}`, "_blank"),
			);
		}
	},
});
