frappe.listview_settings["Attendance"] = Object.assign(
	frappe.listview_settings["Attendance"] || {},
	{
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
