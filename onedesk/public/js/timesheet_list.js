// Time, OneProject's list of timesheets: who, for which project, which days
// and how many hours, billable and all. The ID is on the row's hover, so it
// takes no column (one_hr/custom/timesheet.json has the columns).
frappe.listview_settings["Timesheet"] = Object.assign(frappe.listview_settings["Timesheet"] || {}, {
	hide_name_column: true,
});
