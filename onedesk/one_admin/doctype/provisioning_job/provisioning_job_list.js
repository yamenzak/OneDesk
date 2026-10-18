frappe.listview_settings["Provisioning Job"] = {
	add_fields: ["status", "kind", "step", "attempts", "error"],
	filters: [["status", "!=", "Done"]],
	hide_name_column: true,
	hide_name_filter: true,

	formatters: {
		tenant(value) {
			return (value && frappe.utils.get_link_title("Tenant", value)) || value;
		},
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
