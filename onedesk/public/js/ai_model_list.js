frappe.listview_settings["AI Model"] = {
	hide_name_column: true,
	hide_name_filter: true,
	add_fields: ["status", "offered", "default_for"],

	get_indicator(doc) {
		if (doc.status === "Withdrawn") return [__("Withdrawn"), "grey", "status,=,Withdrawn"];
		if (doc.status !== "Priced") return [__("Needs review"), "orange", "status,=,Needs Review"];
		if (doc.offered && doc.default_for) return [__("Default"), "green", "offered,=,1"];
		return doc.offered
			? [__("Offered"), "green", "offered,=,1"]
			: [__("Not offered"), "blue", "offered,=,0"];
	},

	formatters: {
		input_per_million: (value) => (value ? format_number(value, null, 0) : ""),
		output_per_million: (value) => (value ? format_number(value, null, 0) : ""),
	},

	button: {
		show: (doc) => doc.status === "Priced",
		get_label: (doc) => (doc.offered ? __("Stop Offering") : __("Offer")),
		get_description: (doc) =>
			doc.offered ? __("Stop workspaces from picking this model") : __("Let workspaces pick this model"),
		action(doc) {
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

onedesk.models.sync = (provider, list) => {
	frappe.show_alert({ message: __("Syncing {0}…", [provider]), indicator: "blue" });
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
