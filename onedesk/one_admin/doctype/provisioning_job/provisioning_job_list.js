// The job list answers one question: is anything stuck. So Failed is red,
// Waiting is blue because it is fine and merely slow, and the step is a column
// because a job stuck on the same step for an hour is the one worth opening.
//
// The job's number says nothing, so the workspace leads the row, and a failed
// job's error is on its row under the step, which is what the list is opened
// for. When it last moved is frappe's own, at the row's end.
frappe.listview_settings["Provisioning Job"] = {
	add_fields: ["status", "kind", "step", "attempts", "error"],
	filters: [["status", "!=", "Done"]],
	hide_name_column: true,
	hide_name_filter: true,

	formatters: {
		// The workspace leads the row, by its name rather than its slug.
		tenant(value) {
			return (value && frappe.utils.get_link_title("Tenant", value)) || value;
		},
		// `step` holds a function name. The words come from the boot, which
		// carries `steps.SAID` — one list, read by the list and the form alike.
		step(value, df, doc) {
			if (!value) return "";
			const esc = frappe.utils.escape_html;
			const said = esc((frappe.boot.one_steps || {})[value] || value);
			if (doc.status !== "Failed" || !doc.error) return said;
			const error = String(doc.error).split("\n")[0].slice(0, 120);
			return `${said}<div class="text-danger small ellipsis" title="${esc(doc.error)}">${esc(error)}</div>`;
		},
	},

	get_indicator(doc) {
		const says = {
			Pending: ["orange", __("Waiting to run")],
			Waiting: ["blue", __("Waiting on Frappe Cloud")],
			Done: ["green", __("Done")],
			Failed: ["red", __("Failed")],
		};
		const [colour, word] = says[doc.status] || ["grey", doc.status];
		return [word, colour, `status,=,${doc.status}`];
	},
};
