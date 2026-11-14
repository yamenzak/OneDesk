frappe.listview_settings["Reading Action"] = {
	add_fields: ["audit"],
	get_indicator(doc) {
		if (doc.level === "Done" && doc.audit === "Wrong") return [__("Auditor Disagrees"), "red", "audit,=,Wrong"];
		const tone = { Done: "green", Proposed: "orange", Refused: "gray", Undone: "gray", Dismissed: "gray" }[doc.level];
		return [__(doc.level === "Proposed" ? "Needs Review" : doc.level), tone, `level,=,${doc.level}`];
	},
};
