// Something a model suggested, waiting for a person.
//
// The record is read-only and carries two verbs, which is the whole design: a
// proposal somebody could edit before applying no longer says what the model
// suggested, and the point of the card is that it does.
frappe.ui.form.on("AI Proposal", {
	refresh(frm) {
		if (frm.is_new()) return;
		onedesk.proposal.draw(frm);
		if (frm.doc.state !== "Proposed") return;

		frm.add_custom_button(__("Apply"), () => onedesk.proposal.run(frm, "apply")).addClass(
			"btn-primary",
		);
		frm.add_custom_button(__("Refuse"), () => onedesk.proposal.run(frm, "refuse"));
	},
});

frappe.provide("onedesk.proposal");

onedesk.proposal.SAYS = {
	Proposed: ["orange", __("Waiting for you")],
	Applied: ["green", __("Done")],
	Refused: ["grey", __("Refused")],
	Stale: ["red", __("Out of date")],
};

onedesk.proposal.draw = (frm) => {
	const [colour, word] = onedesk.proposal.SAYS[frm.doc.state] || ["grey", frm.doc.state];
	frm.page.set_indicator(word, colour);

	frm.dashboard.clear_headline();
	if (frm.doc.state === "Stale") {
		frm.dashboard.set_headline(
			__("{0} changed after this was suggested, so it no longer applies.", [frm.doc.record]),
			"red",
		);
		return;
	}
	if (frm.doc.state === "Applied" && frm.doc.applied_doc) {
		frm.dashboard.set_headline(
			__("Done. It wrote {0}.", [frm.doc.applied_doc]),
			"green",
		);
		return;
	}
	if (frm.doc.state === "Proposed") {
		frm.dashboard.set_headline(
			__("Nothing has happened yet. It is checked against your own permissions when you apply it."),
			"blue",
		);
	}
};

// The verb, and then away: whichever way it is answered the card is settled,
// and a settled card is not a screen anybody stays on.
onedesk.proposal.run = (frm, verb) => {
	frappe.confirm(
		verb === "apply"
			? __("Do this now, as you?")
			: __("Say no to this?"),
		() =>
			frappe
				.xcall(`onedesk.one_ai.run.${verb}`, { proposal: frm.doc.name })
				.then((out) => {
					frm.reload_doc();
					if (out.record) {
						frappe.show_alert({
							message: __("Done. It wrote {0}.", [out.record]),
							indicator: "green",
						});
					}
				}),
	);
};
