frappe.ui.form.on("Credit Ledger Entry", {
	refresh(frm) {
		frm.sidebar.sidebar.find(".form-shared").addClass("hidden");
		const ref = frm.doc.reference;
		if (frm.is_new() || !ref) return;
		if (frm.doc.source === "Plan" && frm.doc.kind === "Grant") {
			frm.add_custom_button(__("Open Plan"), () => frappe.set_route("Form", "Offering", ref));
		}
		if (frm.doc.source === "Purchase" && ref.startsWith("cs_")) {
			const test = ref.startsWith("cs_test_") ? "test/" : "";
			frm.page.add_menu_item(__("Open in Stripe"), () =>
				window.open(`https://dashboard.stripe.com/${test}search?query=${encodeURIComponent(ref)}`, "_blank"),
			);
		}
		frm.page.add_menu_item(__("AI Usage"), () =>
			frappe.set_route("query-report", "AI Usage", { tenant: frm.doc.tenant, by: "Model" }),
		);
	},
});
