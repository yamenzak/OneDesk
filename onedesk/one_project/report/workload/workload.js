// Who has how many hours of open work in a week (report/workload/workload.py).
// Figures, not a chart: over capacity and late are red, and a person's tasks
// open their list.
frappe.query_reports["Workload"] = {
	filters: [
		{ fieldname: "week", label: __("Week Of"), fieldtype: "Date", default: frappe.datetime.get_today(), reqd: 1 },
		{ fieldname: "project", label: __("Project"), fieldtype: "Link", options: "Project" },
	],
	formatter(value, row, column, data, default_formatter) {
		const shown = default_formatter(value, row, column, data);
		if (!data) return shown;
		if ((column.fieldname === "free" && data.free < 0) || (column.fieldname === "load" && data.load > 100)) {
			return `<span class="text-danger">${shown}</span>`;
		}
		if (column.fieldname === "late" && data.late) return `<span class="text-danger">${shown}</span>`;
		if (column.fieldname === "tasks" && data.tasks) {
			const assigned = encodeURIComponent(JSON.stringify(["like", `%${data.user}%`]));
			const open = encodeURIComponent(JSON.stringify(["in", ["Open", "Working", "Pending Review"]]));
			return `<a href="/desk/task?_assign=${assigned}&status=${open}">${shown}</a>`;
		}
		return shown;
	},
};
