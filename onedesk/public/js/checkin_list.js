frappe.listview_settings["Employee Checkin"] = Object.assign(
	frappe.listview_settings["Employee Checkin"] || {},
	{
		add_fields: ["attendance", "skip_auto_attendance", "one_outcome"],

		get_indicator: function (doc) {
			if (doc.skip_auto_attendance) {
				return [__("Rejected"), "red", "skip_auto_attendance,=,1"];
			}
			if (doc.attendance) {
				return [__("Counted"), "green", "attendance,is,set"];
			}
			if (doc.one_outcome === "Flagged") {
				return [__("Flagged"), "orange", "one_outcome,=,Flagged"];
			}
			return [__("Not counted yet"), "gray", "attendance,is,not set"];
		},
	},
);
