// How far each project has got (report/project_progress/project_progress.py):
// ERPNext's Project Summary without the HR checklists. Its Company and Is
// Active go (one workspace is one company, and Status says whether a project
// is still going), and so does its Project Type, which is ERPNext's and not
// the kind a project is in One.
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
