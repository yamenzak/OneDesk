// Tasks on frappe's Calendar: ERPNext's settings (task_calendar.js), read
// through one_task/views.py `events`, which leaves a template's tasks out and
// draws a task planned by the day as a day. ERPNext keeps a task's dates as
// datetimes at midnight, so every task read "12:00 AM".
Object.assign(frappe.views.calendar["Task"] || (frappe.views.calendar["Task"] = {}), {
	get_events_method: "onedesk.one_task.views.events",
});
