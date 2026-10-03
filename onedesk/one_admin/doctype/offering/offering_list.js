// The price list: plans, then add-ons, then packs, each by price (`sort_key`),
// with what each costs and gives in words. A disabled one is greyed as
// Disabled; the others say their kind. The signup page reads the same rows,
// so the menu opens it as a customer sees it.
frappe.listview_settings["Offering"] = {
	add_fields: ["kind", "enabled", "recurring", "currency", "amount"],
	hide_name_column: true,
	hide_name_filter: true,

	onload(listview) {
		listview.page.add_menu_item(__("View Signup Page"), () => window.open("/start", "_blank"));
	},

	get_indicator(doc) {
		if (!doc.enabled) return [__("Disabled"), "grey", "enabled,=,0"];
		const colour = { Plan: "blue", "Add-on": "purple", "Credit Pack": "green" }[doc.kind] || "grey";
		return [__(doc.kind), colour, `kind,=,${doc.kind}`];
	},

	formatters: {
		amount(value, df, doc) {
			const price = format_currency(value, doc.currency, 0);
			return doc.recurring ? __("{0} a month", [price]) : __("{0} once", [price]);
		},
	},
};
