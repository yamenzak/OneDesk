frappe.listview_settings["Reading Action"] = {
	get_indicator(doc) {
		const tone = { Done: "green", Proposed: "orange", Refused: "gray", Undone: "gray", Dismissed: "gray" }[doc.level];
		return [__(doc.level === "Proposed" ? "Needs Review" : doc.level), tone, `level,=,${doc.level}`];
	},
};
