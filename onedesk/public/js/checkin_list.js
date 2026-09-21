// The one question this list is asked is whether a log counted, and nothing
// answered it: hrms leaves the indicator empty because Employee Checkin is not
// submittable, so every row showed a blank Status.
frappe.listview_settings["Employee Checkin"] = Object.assign(
	frappe.listview_settings["Employee Checkin"] || {},
	{
		add_fields: ["attendance", "skip_auto_attendance", "one_outcome"],

		get_indicator: function (doc) {
			// A reviewer threw this one out, so it will never become a day.
			if (doc.skip_auto_attendance) {
				return [__("Rejected"), "red", "skip_auto_attendance,=,1"];
			}
			if (doc.attendance) {
				return [__("Counted"), "green", "attendance,is,set"];
			}
			if (doc.one_outcome === "Flagged") {
				return [__("Flagged"), "orange", "one_outcome,=,Flagged"];
			}
			// The shift processes the day on its own schedule, so a log written
			// minutes ago is waiting rather than wrong.
			return [__("Not counted yet"), "gray", "attendance,is,not set"];
		},
	},
);
