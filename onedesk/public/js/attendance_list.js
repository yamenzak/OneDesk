// Loaded after hrms's own attendance_list.js, which assigns the whole settings
// object; merge rather than replace, or the Mark Attendance dialog goes with it.
frappe.listview_settings["Attendance"] = Object.assign(
	frappe.listview_settings["Attendance"] || {},
	{
		// Approved leave is not absence, and working from home is not the office.
		// The colours are the ones the attendance heatmap uses.
		get_indicator: function (doc) {
			const colour = {
				Present: "green",
				"Work From Home": "cyan",
				"Half Day": "orange",
				"On Leave": "blue",
				Absent: "red",
			}[doc.status];

			if (colour) {
				return [__(doc.status), colour, "status,=," + doc.status];
			}
		},
	},
);
