// The model catalogue, from the operator's side.
//
// Nothing on this list is typed. The rows arrive from each provider's API and
// their prices from each provider's published page, nightly — so the list's
// only verb is to do that now rather than wait, which is what somebody wants
// the morning a provider ships a model.
frappe.listview_settings["AI Model"] = {
	hide_name_column: true,
	add_fields: ["status", "offered"],

	get_indicator(doc) {
		if (doc.status === "Withdrawn") return [__("Withdrawn"), "grey", "status,=,Withdrawn"];
		if (doc.status !== "Priced") return [__("Needs review"), "orange", "status,=,Needs Review"];
		return doc.offered
			? [__("Offered"), "green", "offered,=,1"]
			: [__("Not offered"), "blue", "offered,=,0"];
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
