frappe.listview_settings["Offering"] = {
	add_fields: ["kind", "enabled", "recurring", "currency", "amount"],
	hide_name_column: true,
	hide_name_filter: true,

	onload(listview) {
		listview.page.add_menu_item(__("View Signup Page"), () => window.open("/start", "_blank"));
		listview.page.add_menu_item(__("OneCredit Rates"), async () => {
			const rows = await frappe.xcall("onedesk.one_admin.offerings.rates");
			const cell = (text) => frappe.utils.escape_html(String(text));
			const body = rows
				.map((one) => `<tr><td>${cell(one.what)}</td><td>${cell(one.per)}</td><td class="text-right">${cell(format_number(one.credits, null, 4))}</td></tr>`)
				.join("");
			new frappe.ui.Dialog({
				title: __("OneCredit Rates"),
				fields: [
					{
						fieldtype: "HTML",
						options: `<table class="table table-bordered"><thead><tr><th>${__("Use")}</th><th>${__("Per")}</th><th class="text-right">${__("Credits")}</th></tr></thead><tbody>${body}</tbody></table>`,
					},
				],
			}).show();
		});
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
