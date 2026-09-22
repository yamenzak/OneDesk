// What this workspace wants one action to run on, and what it wants added.
//
// Two things make this screen worth drawing rather than a pair of fields: the
// model list comes from the account rather than from here, filtered to what the
// action needs; and the instruction the action already carries is shown, so
// that "added" reads as added rather than as the only thing being said.
frappe.ui.form.on("AI Action Setting", {
	refresh(frm) {
		onedesk.action.draw(frm);
		if (!frm.is_new() && frm.doc.action) {
			frm.add_custom_button(__("Try it"), () => onedesk.action.tryIt(frm));
		}
	},
	action(frm) {
		onedesk.action.draw(frm);
	},
});

frappe.provide("onedesk.action");

onedesk.action.draw = (frm) => {
	frm.dashboard.clear_headline();
	frm.set_df_property("model", "options", [""]);
	if (!frm.doc.action) return;

	frappe.db
		.get_doc("AI Action", frm.doc.action)
		.then((asked) => {
			frm.dashboard.set_headline(
				__("{0} runs on a model that can do {1}. Anything added below is added to the instruction it already carries, and never replaces it.", [
					asked.label,
					asked.capability.toLowerCase(),
				]),
				"blue",
			);
			onedesk.action.ours(frm, asked);
			return frappe.xcall("onedesk.one_ai.run.models", { needs: asked.capability });
		})
		.then((models) => onedesk.action.pick(frm, models || []))
		.catch(() => {});
};

// The account's list, not ours. A workspace holds no catalogue, so an empty
// answer means the account offers nothing for this rather than that something
// went wrong here.
onedesk.action.pick = (frm, models) => {
	const named = models.map((m) => m.name);
	frm.set_df_property("model", "options", [""].concat(named));
	const fallback = models.find((m) => m.default);
	frm.set_df_property(
		"model",
		"description",
		models.length
			? fallback
				? __("Empty uses {0}.", [fallback.label || fallback.name])
				: __("Empty uses whichever model the account has set as the default for this.")
			: __("The account offers no model that can do this yet."),
	);
	frm.refresh_field("model");
};

onedesk.action.ours = (frm, asked) => {
	const field = frm.get_field("extra");
	if (!field) return;
	frm.set_df_property(
		"extra",
		"description",
		__("Added after this:") + "\n" + (asked.instruction || ""),
	);
	frm.refresh_field("extra");
};

// Run it and read the answer. Charged like any other call — a preview that is
// not charged is a preview of something else.
onedesk.action.tryIt = (frm) => {
	const asking = new frappe.ui.Dialog({
		title: __("Try it"),
		fields: [
			{ fieldname: "text", fieldtype: "Small Text", label: __("Text"), reqd: 1 },
			{ fieldname: "said", fieldtype: "HTML" },
		],
		primary_action_label: __("Run"),
		primary_action(values) {
			const where = asking.fields_dict.said.$wrapper;
			where.html(`<p class="text-muted">${__("Asking…")}</p>`);
			frappe
				.xcall("onedesk.one_ai.run.try_it", { action: frm.doc.action, text: values.text })
				.then((out) =>
					where.html(
						`<p>${frappe.utils.escape_html(out.said || "")}</p>` +
							`<p class="text-muted">${__("{0} credits.", [out.credits])}</p>`,
					),
				)
				.catch(() => where.empty());
		},
	});
	asking.show();
};
