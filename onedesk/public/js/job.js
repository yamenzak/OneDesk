// A provisioning job, from the operator's side.
//
// The record is read-only for the same reason a workspace is: every field on it
// is written by the runner, and a Status somebody can set to Done is a job that
// silently stops walking with a site half built.
//
// What it gains instead is the one thing the record never said — where in the
// walk it is. `step` holds a function name, which tells a reader nothing; the
// server turns that into a list of sentences and a position, so a job that
// stopped says it stopped while asking press to destroy the site.
frappe.ui.form.on("Provisioning Job", {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.page.clear_indicator();

		frappe.xcall("onedesk.one_admin.operator.walk", { job: frm.doc.name }).then((walk) => {
			onedesk.job.draw(frm, walk);
		});
	},
});

frappe.provide("onedesk.job");

onedesk.job.SAYS = {
	Pending: ["orange", __("Waiting to run")],
	Waiting: ["blue", __("Waiting on Frappe Cloud")],
	Done: ["green", __("Done")],
	Failed: ["red", __("Stopped")],
};

onedesk.job.draw = (frm, walk) => {
	const [colour, word] = onedesk.job.SAYS[walk.status] || ["grey", walk.status];
	frm.page.set_indicator(word, colour);

	// Frappe's own progress bar, the same one a sales order uses for how much of
	// it has shipped. Two segments rather than one: what is done, and the step
	// it is on — which is the step that failed when it failed.
	if (walk.of) {
		const one = 100 / walk.of;
		const here = walk.status === "Failed" ? "progress-bar-danger" : "progress-bar-warning";
		frm.dashboard.add_progress(
			__("Steps"),
			walk.status === "Done"
				? [{ width: "100%", progress_class: "progress-bar-success", title: __("Done") }]
				: [
						{
							width: `${walk.at * one}%`,
							progress_class: "progress-bar-success",
							title: __("Done"),
						},
						{ width: `${one}%`, progress_class: here, title: __("Now") },
					],
			onedesk.job.where(walk),
		);
	}

	if (walk.status === "Failed") {
		frm.add_custom_button(__("Resume"), () => {
			frappe.confirm(
				__("Run {0} again, from the step it stopped on?", [frm.doc.name]),
				() =>
					frappe
						.xcall("onedesk.one_admin.operator.resume", { job: frm.doc.name })
						.then(() => frm.reload_doc()),
			);
		}).addClass("btn-primary");
	}
};

// The sentence under the bar. A job that is done says so; one that stopped says
// where, because that is the only thing anybody opens this screen to find out.
//
// A colon rather than a dash and a lower-cased step: the step names a proper
// noun, and `toLowerCase` turned Frappe Cloud into frappe cloud.
onedesk.job.where = (walk) => {
	if (walk.status === "Done") return __("Finished all {0} steps.", [walk.of]);
	const now = walk.steps[walk.at];
	const said = now ? now.said : __("the start");
	if (walk.status === "Failed") {
		return __("Stopped at step {0} of {1}: {2}.", [walk.at + 1, walk.of, said]);
	}
	const tried = walk.attempts
		? " " + __("Tried {0} times.", [walk.attempts])
		: "";
	return __("Step {0} of {1}: {2}.", [walk.at + 1, walk.of, said]) + tried;
};
