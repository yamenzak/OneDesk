// What stopping a task's timer did, said the same on the task and on My Tasks.
// See one_task/timer.py.
frappe.provide("onedesk.task_timer");

// What stopping did: the hours added, or nothing for a timer stopped at once.
onedesk.task_timer.stopped = (hours) =>
	frappe.ui.toast(
		hours
			? { message: __("{0} added to your timesheet.", [frappe.utils.get_formatted_duration(hours * 3600)]), type: "success" }
			: { message: __("Stopped within a minute, so nothing was added."), type: "info" }
	);
