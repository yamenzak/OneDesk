// An appraisal says whose it is and where the score stands.
//
// The record opens on Employee, Appraisal Cycle, Department, Designation and a
// Final Score of 0, and the 0 is the whole difficulty: it reads like a verdict
// and means "nothing has been rated yet". The three numbers behind it — the
// goal score, the average feedback score and the self appraisal — are each on
// their own tab, so working out which of the three is missing costs three
// clicks.
frappe.ui.form.on("Appraisal", {
	refresh: (frm) => onedesk.appraisal.say(frm),
	final_score: (frm) => onedesk.appraisal.say(frm),
});

frappe.provide("onedesk.appraisal");

onedesk.appraisal.say = (frm) => {
	if (frm.is_new()) {
		frm.dashboard.clear_headline();
		return;
	}

	const missing = [];
	if (!flt(frm.doc.goal_score_percentage)) missing.push(__("goals"));
	if (!flt(frm.doc.avg_feedback_score)) missing.push(__("feedback"));
	if (!flt(frm.doc.self_score)) missing.push(__("the self appraisal"));

	const period = frm.doc.start_date && frm.doc.end_date
		? __("{0} to {1}", [
				frappe.datetime.str_to_user(frm.doc.start_date),
				frappe.datetime.str_to_user(frm.doc.end_date),
		  ])
		: frm.doc.appraisal_cycle;

	if (missing.length === 3) {
		onedesk.decision.headline(
			frm,
			__("{0}, {1}. Nothing has been rated yet, so the score is not a verdict.", [
				frm.doc.employee_name,
				period,
			]),
			"orange"
		);
		return;
	}

	const score = __("{0} out of 5", [flt(frm.doc.final_score, 2)]);
	onedesk.decision.headline(
		frm,
		missing.length
			? __("{0}, {1} — {2}, still waiting on {3}.", [
					frm.doc.employee_name,
					period,
					score,
					missing.join(", "),
			  ])
			: __("{0}, {1} — {2}.", [frm.doc.employee_name, period, score]),
		missing.length ? "orange" : "green"
	);
};
