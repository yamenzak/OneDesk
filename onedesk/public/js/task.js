// A timer on the task itself: Start Timer adds a row to the person's timesheet
// for the week, Stop Timer ends it. See one_task/timer.py. Only for people who
// may keep a timesheet, which the server checks again when it saves one.
frappe.provide("onedesk.task_timer");

onedesk.task_timer.button = async (frm) => {
	if (frm.is_new() || !frappe.model.can_create("Timesheet")) return;
	const running = await frappe.xcall("onedesk.one_task.timer.running");
	const here = running && running.task === frm.doc.name;
	const since = here ? moment(running.since).format("HH:mm") : null;
	frm.add_custom_button(here ? __("Stop Timer (since {0})", [since]) : __("Start Timer"), async () => {
		if (here) onedesk.task_timer.stopped(await frappe.xcall("onedesk.one_task.timer.stop"));
		else await frappe.xcall("onedesk.one_task.timer.start", { task: frm.doc.name });
		frm.reload_doc();
	});
};

frappe.ui.form.on("Task", {
	refresh(frm) {
		onedesk.task_timer.button(frm);
	},
});
