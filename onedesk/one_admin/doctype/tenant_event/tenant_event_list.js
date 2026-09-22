// A log, so it is read and never opened. The colour is the whole of what a row
// says at a glance: the two that cost a customer something are red, the two
// that are a warning are orange, and coming back is green.
frappe.listview_settings["Tenant Event"] = {
	add_fields: ["kind"],
	// The name is a hash. On a log it is the least useful thing on the row.
	hide_name_column: true,

	get_indicator(doc) {
		const says = {
			"Over Storage": "orange",
			Overdue: "orange",
			Suspended: "red",
			Dropped: "red",
			Archived: "grey",
			Restored: "green",
			Drifted: "orange",
		};
		return [__(doc.kind), says[doc.kind] || "grey", `kind,=,${doc.kind}`];
	},
};
