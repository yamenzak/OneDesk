// Flagged first and unreviewed only, because a queue that opens on everything
// ever recorded is a list rather than a queue.
frappe.listview_settings["Clock Attempt"] = {
	add_fields: ["outcome", "verdict", "score"],
	// `verdict in [""]` is dropped on the way to the list, which left every
	// reviewed attempt in the queue. "is not set" survives.
	filters: [
		["outcome", "=", "Flagged"],
		["verdict", "is", "not set"],
	],
	get_indicator(doc) {
		if (doc.verdict) {
			return [__(doc.verdict), doc.verdict === "Accepted" ? "green" : "red", `verdict,=,${doc.verdict}`];
		}
		const colour = { Allowed: "green", Flagged: "orange", Refused: "red" }[doc.outcome] || "gray";
		return [__(doc.outcome), colour, `outcome,=,${doc.outcome}`];
	},
};
