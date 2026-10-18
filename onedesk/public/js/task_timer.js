frappe.provide("onedesk.task_timer");

onedesk.task_timer.stopped = (hours) =>
	frappe.ui.toast(
		hours
			? { message: __("{0} added to your timesheet.", [frappe.utils.get_formatted_duration(hours * 3600)]), type: "success" }
			: { message: __("Under a minute. Nothing added."), type: "info" }
	);
