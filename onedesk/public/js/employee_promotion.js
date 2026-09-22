// A promotion says what it changes.
//
// The list was Employee Name, Draft and the ID, and the record's own header is
// the same three: what actually changed is three rows down in Promotion
// Details, which is a child table and so cannot be a column, cannot be
// filtered and cannot be searched. `one_becomes` carries the new designation up
// onto the document; this says the whole change in one line.
frappe.ui.form.on("Employee Promotion", {
	refresh: (frm) => onedesk.promotion.say(frm),
	promotion_date: (frm) => onedesk.promotion.say(frm),
});

frappe.ui.form.on("Employee Property History", {
	promotion_details_remove: (frm) => onedesk.promotion.say(frm),
	new: (frm) => onedesk.promotion.say(frm),
	property: (frm) => onedesk.promotion.say(frm),
});

frappe.provide("onedesk.promotion");

onedesk.promotion.say = (frm) => {
	if (frm.is_new() || !frm.doc.promotion_date) {
		frm.dashboard.clear_headline();
		return;
	}

	const changes = (frm.doc.promotion_details || [])
		.filter((row) => row.property && row.new)
		.map((row) =>
			row.current
				? __("{0} {1} → {2}", [row.property.toLowerCase(), row.current, row.new])
				: __("{0} becomes {1}", [row.property.toLowerCase(), row.new])
		);

	const when = frappe.datetime.str_to_user(frm.doc.promotion_date);
	onedesk.decision.headline(
		frm,
		changes.length
			? __("{0}, from {1}: {2}.", [frm.doc.employee_name, when, changes.join(", ")])
			: __("{0}, from {1}. Nothing is listed as changing yet.", [frm.doc.employee_name, when]),
		changes.length ? "blue" : "orange"
	);
};
