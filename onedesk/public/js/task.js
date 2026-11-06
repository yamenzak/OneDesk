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

onedesk.task_timer.repeats = async (frm) => {
	if (frm.is_new() || !frm.doc.auto_repeat || !frm.perm[0]?.write) return;
	const repeat = await frappe.xcall("onedesk.one_task.task.repeat_of", { task: frm.doc.name });
	if (!repeat || repeat.disabled) return;
	frm.add_custom_button(
		__("Stop Repeating"),
		async () => {
			const go = await onedesk.interface.ask({
				question: __("Stop repeating {0}?", [frm.doc.subject]),
				effect: __("No new task is made from it. This one stays as it is."),
				verb: __("Stop Repeating"),
			});
			if (!go) return;
			await frappe.xcall("onedesk.one_task.task.stop_repeat", { task: frm.doc.name });
			frappe.show_alert({ message: __("Repeating stopped."), indicator: "green" });
			frm.reload_doc();
		},
		__("Actions")
	);
};

frappe.ui.form.on("Task", {
	refresh(frm) {
		onedesk.task_timer.button(frm);
		onedesk.task_timer.repeats(frm);
	},
});
