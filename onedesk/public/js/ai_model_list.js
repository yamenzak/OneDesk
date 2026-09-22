// The model catalogue, from the operator's side.
//
// Nothing on this list is typed. The rows arrive from each provider's API and
// their prices from each provider's published page, nightly — so the verbs are
// to do that now rather than wait, which is what somebody wants the morning a
// provider ships a model, and the one decision that is the operator's rather
// than the provider's: whether to sell it. That is one press on the row.
frappe.listview_settings["AI Model"] = {
	hide_name_column: true,
	add_fields: ["status", "offered", "default_for"],

	get_indicator(doc) {
		if (doc.status === "Withdrawn") return [__("Withdrawn"), "grey", "status,=,Withdrawn"];
		if (doc.status !== "Priced") return [__("Needs review"), "orange", "status,=,Needs Review"];
		// The capability it is the default for is on the row already.
		if (doc.offered && doc.default_for) return [__("Default"), "green", "offered,=,1"];
		return doc.offered
			? [__("Offered"), "green", "offered,=,1"]
			: [__("Not offered"), "blue", "offered,=,0"];
	},

	// What a million tokens in and out sell for, after markup. Zero is "not
	// priced in tokens" — an image model — and printed as 0.00 it reads as free.
	formatters: {
		input_per_million: (value) => (value ? format_number(value, null, 0) : ""),
		output_per_million: (value) => (value ? format_number(value, null, 0) : ""),
	},

	button: {
		show: (doc) => doc.status === "Priced",
		get_label: (doc) => (doc.offered ? __("Stop offering") : __("Offer")),
		get_description: (doc) =>
			doc.offered ? __("Workspaces can no longer pick this model") : __("Let workspaces pick this model"),
		action(doc) {
			// The model's own save, so every rule on it still applies — a default
			// cannot stop being offered while it is the default.
			frappe
				.xcall("frappe.client.set_value", {
					doctype: "AI Model",
					name: doc.name,
					fieldname: "offered",
					value: doc.offered ? 0 : 1,
				})
				.then(() => cur_list.refresh());
		},
	},

	onload(list) {
		for (const provider of ["workers-ai", "google-ai-studio"]) {
			list.page.add_menu_item(__("Sync {0}", [provider]), () =>
				onedesk.models.sync(provider, list),
			);
		}
	},
};

frappe.provide("onedesk.models");

// The count back rather than the rows: the list is about to redraw anyway, and
// the one thing worth a sentence is how many need a person to look at them.
onedesk.models.sync = (provider, list) => {
	frappe.show_alert({ message: __("Asking {0}…", [provider]), indicator: "blue" });
	frappe
		.xcall("onedesk.one_admin.operator.sync_catalogue", { provider })
		.then((count) => {
			frappe.show_alert({
				message: __("{0} models, {1} priced, {2} need review.", [
					count.seen,
					count.priced,
					count.review,
				]),
				indicator: count.review ? "orange" : "green",
			});
			list.refresh();
		});
};
