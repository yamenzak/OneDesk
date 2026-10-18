frappe.query_reports["Project Progress"] = {
	filters: [
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: ["", "Open", "On hold", "Completed", "Cancelled"].map((value) => ({ value, label: value ? __(value) : "" })),
			default: "Open",
		},
		{
			fieldname: "priority",
			label: __("Priority"),
			fieldtype: "Select",
			options: ["", "Low", "Medium", "High"].map((value) => ({ value, label: value ? __(value) : "" })),
		},
	],
};
