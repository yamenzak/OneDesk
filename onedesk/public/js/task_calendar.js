Object.assign(frappe.views.calendar["Task"] || (frappe.views.calendar["Task"] = {}), {
	get_events_method: "onedesk.one_task.views.events",
});
