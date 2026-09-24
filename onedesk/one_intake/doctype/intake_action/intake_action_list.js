// Needs a Look: what OneAI proposed and waits for a person, first.
frappe.listview_settings["Intake Action"] = {
	get_indicator(doc) {
		const tone = { Done: "green", Proposed: "orange", Refused: "gray", Undone: "gray", Dismissed: "gray" }[doc.level];
		return [__(doc.level === "Proposed" ? "Needs a look" : doc.level), tone, `level,=,${doc.level}`];
	},
};
