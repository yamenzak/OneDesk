// The credit ledger, from the operator's side.
//
// Read-only by construction: an entry is submitted when it is written and there
// is no balance field anywhere to edit. What a reader wants from the list is
// which way each row moved money, which is the indicator.
frappe.listview_settings["Credit Ledger Entry"] = {
	hide_name_column: true,
	add_fields: ["kind", "credits", "expires_on"],

	get_indicator(doc) {
		if (doc.kind === "Grant") {
			const gone = doc.expires_on && doc.expires_on < frappe.datetime.get_today();
			return gone
				? [__("Expired"), "grey", "kind,=,Grant"]
				: [__("Granted"), "green", "kind,=,Grant"];
		}
		if (doc.kind === "Refund") return [__("Refunded"), "blue", "kind,=,Refund"];
		return [__("Spent"), "orange", "kind,=,Spend"];
	},
};
