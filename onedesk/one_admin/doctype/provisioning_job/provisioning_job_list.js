// The job list answers one question: is anything stuck. So Failed is red,
// Waiting is blue because it is fine and merely slow, and the step is a column
// because a job stuck on the same step for an hour is the one worth opening.
frappe.listview_settings["Provisioning Job"] = {
	add_fields: ["status", "kind", "step", "attempts"],
	filters: [["status", "!=", "Done"]],

	formatters: {
		// `step` holds a function name. The words come from the boot, which
		// carries `steps.SAID` — one list, read by the list and the form alike.
		step(value) {
			if (!value) return "";
			return (frappe.boot.one_steps || {})[value] || value;
		},
	},

	get_indicator(doc) {
		const says = {
			Pending: ["orange", __("Waiting to run")],
			Waiting: ["blue", __("Waiting on Frappe Cloud")],
			Done: ["green", __("Done")],
			Failed: ["red", __("Stopped")],
		};
		const [colour, word] = says[doc.status] || ["grey", doc.status];
		return [word, colour, `status,=,${doc.status}`];
	},
};
