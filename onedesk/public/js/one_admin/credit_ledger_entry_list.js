frappe.listview_settings["Credit Ledger Entry"] = {
	hide_name_column: true,
	hide_name_filter: true,
	add_fields: ["kind", "credits", "expires_on", "source"],
	filters: [["source", "!=", "Run"]],

	get_indicator(doc) {
		if (doc.kind === "Grant") {
			const gone = doc.expires_on && doc.expires_on < frappe.datetime.get_today();
			return gone
				? [__("Expired"), "grey", "kind,=,Grant"]
				: [__("Granted"), "green", "kind,=,Grant"];
		}
		if (doc.kind === "Refund") return [__("Refunded"), "blue", "kind,=,Refund"];
		if (doc.source === "Operator") return [__("Revoked"), "red", "kind,=,Spend"];
		return [__("Spent"), "orange", "kind,=,Spend"];
	},

	formatters: {
		credits: (value) => format_number(value, null, 2),
	},
};
