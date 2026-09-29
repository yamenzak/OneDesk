// A job, from the operator's side.
//
// Read-only: the machinery writes it. Where it is in its walk is the head
// (one_admin/heads.py); below it, the walk itself, every step in words with
// the ones done ticked, the one it is on marked, and a failed one's error
// under it. The step's own field is a function name, so it is not shown, and
// its attempts and error are said under the step rather than twice.
frappe.ui.form.on("Provisioning Job", {
	refresh(frm) {
		// The walk below says the step, how often it was tried and the error.
		frm.toggle_display(["step", "attempts", "error"], false);
		frm.sidebar.sidebar.find(".form-shared").addClass("hidden");
		if (frm.is_new()) return;
		frappe
			.xcall("onedesk.one_admin.operator.walk", { job: frm.doc.name })
			.then((walk) => onedesk.job.draw(frm, walk));
	},
});

frappe.provide("onedesk.job");

onedesk.job.draw = (frm, walk) => {
	const field = frm.get_field("walk_said");
	if (!field) return;
	const esc = frappe.utils.escape_html;
	const rows = walk.steps.map((step, i) => {
		const here = i === walk.at && walk.status !== "Done";
		const failed = here && walk.status === "Failed";
		const icon = step.done || walk.status === "Done" ? "check" : failed ? "x" : here ? "loader" : "circle";
		const tone = failed ? "text-danger" : step.done || walk.status === "Done" ? "" : here ? "" : "text-muted";
		const weight = here ? "bold" : "";
		// Under the step it is on: how often it was tried, and what the last
		// try answered, in red once it has failed.
		const said = here
			? [walk.attempts && !failed ? __("Tried {0} times", [walk.attempts]) : "", walk.error || ""].filter(Boolean)
			: [];
		const note = said.length
			? `<div class="${failed ? "text-danger" : "text-muted"} small" style="margin-left:24px">${said.map(esc).join(" · ")}</div>`
			: "";
		return `<div class="${tone}" style="padding:4px 0">
			<span style="display:inline-flex;gap:8px;align-items:center" class="${weight}">
				${frappe.utils.icon(icon, "sm")}<span>${esc(step.said)}</span>
			</span>${note}
		</div>`;
	});
	field.$wrapper.html(`<div>${rows.join("")}</div>`);
};
