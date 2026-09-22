// A plan, a credit pack or an add-on, from the operator's side.
//
// This is the one screen in the console that is genuinely typed, because a price
// list is a decision rather than a record of something that happened. The screen
// adds the one fact that decides every edit on it: how many workspaces are on
// this offering already.
frappe.ui.form.on("Offering", {
	refresh(frm) {
		if (frm.is_new()) return;
		frappe
			.xcall("onedesk.one_admin.operator.sold", { offering: frm.doc.name })
			.then((count) => onedesk.offering.draw(frm, count));
	},
	enabled(frm) {
		if (frm.doc.enabled || frm.is_new()) return;
		frappe.show_alert({
			message: __("Existing workspaces keep what they bought. This only stops new signups."),
			indicator: "blue",
		});
	},
});

frappe.provide("onedesk.offering");

// Quotas are copied onto a workspace when it signs up, not read back through the
// offering, so editing them here changes nothing for anybody who already bought.
// That is deliberate — see signup._tenant_for — and it is the thing an operator
// has to know before changing a number on this screen.
onedesk.offering.draw = (frm, count) => {
	frm.dashboard.clear_headline();
	if (!count.all) {
		frm.dashboard.set_headline(__("No workspace has bought this yet."), "blue");
		return;
	}
	const many = count.all === 1 ? __("One workspace bought this") : __("{0} workspaces bought this", [count.all]);
	const on = count.live
		? many + ", " + __("{0} of them live.", [count.live])
		: many + ", " + __("none of them live.");
	frm.dashboard.set_headline(
		on + " " + __("Changing a price or a quota here does not change theirs."),
		"orange",
	);
};
