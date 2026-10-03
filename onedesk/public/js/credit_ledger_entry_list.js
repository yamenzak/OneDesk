// The credit ledger, from the operator's side.
//
// Read-only by construction: an entry is submitted when it is written and there
// is no balance field anywhere to edit. What a reader wants from the list is
// which way each row moved money, which is the indicator, and what people did:
// grants, refunds, and credits taken back. A call's spend is one AI call,
// hundreds a day, and AI Usage is where they are summed. So the list opens on
// everything but calls, which are one filter away.
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
		// Credits are kept to six places, and read to two.
		credits: (value) => format_number(value, null, 2),
	},
};
