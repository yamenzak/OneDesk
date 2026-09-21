// The two buttons that end a flag. Offered on a flagged attempt nobody has
// settled yet, and to somebody who may write one — an employee reading their
// own attempt sees the reasons and no way to wave them through.
frappe.ui.form.on("Clock Attempt", {
	refresh(frm) {
		frm.page.set_indicator(
			__(frm.doc.verdict || frm.doc.outcome),
			onedesk.clock_attempt.COLOUR[frm.doc.verdict || frm.doc.outcome] || "gray"
		);

		// Nothing on this record may be edited, and the grid still draws a
		// selection box and a pencil per row. `editable_grid: 0` stops the
		// typing, not the furniture, so the furniture is hidden in desk.css.
		frm.get_field("signals")?.$wrapper.addClass("one-static-grid");

		if (frm.doc.outcome !== "Flagged" || frm.doc.verdict) return;
		if (!frappe.model.can_write("Clock Attempt")) return;

		frm.page.set_primary_action(__("Accept"), () =>
			onedesk.clock_attempt.settle(frm, "accept", __("Accept this check-in?")));
		frm.add_custom_button(__("Reject"), () =>
			onedesk.clock_attempt.settle(frm, "reject",
				__("Reject it? The check-in stays on the record and stops counting towards the day.")));
	},
});

frappe.provide("onedesk.clock_attempt");

//: What the indicator says, by verdict first and outcome second.
onedesk.clock_attempt.COLOUR = {
	Accepted: "green",
	Rejected: "red",
	Allowed: "green",
	Flagged: "orange",
	Refused: "red",
};

// A note is asked for rather than typed into the record afterwards: the reason
// somebody waved a flag through is the part worth having later, and a field
// nobody is prompted to fill is a field nobody fills.
onedesk.clock_attempt.settle = (frm, verb, question) => {
	frappe.prompt(
		[{ fieldname: "note", fieldtype: "Small Text", label: __("Note"), reqd: verb === "reject" }],
		({ note }) => {
			frappe.xcall(`onedesk.one_hr.review.${verb}`, { attempt: frm.doc.name, note })
				.then(() => {
					frappe.show_alert({ message: __("Reviewed"), indicator: "green" });
					frm.reload_doc();
				});
		},
		question,
		__("Save")
	);
};
