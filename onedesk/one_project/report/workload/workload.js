// Who has how many hours of open work in a week (report/workload/workload.py).
// Figures, not a chart: the team's week in the cards above, over capacity and
// late in red, and a person's tasks, late tasks and tasks not estimated open
// their list. Everyone on an open project's team is listed, free or not.
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
		// Tasks, Late and Not Estimated open the person's tasks they count.
		const narrow = { tasks: {}, late: { exp_end_date: ["<", frappe.datetime.get_today()] }, unestimated: { expected_time: 0 } }[column.fieldname];
		if (narrow && data[column.fieldname]) {
			const where = { _assign: ["like", `%${data.user}%`], status: ["in", ["Open", "Working", "Pending Review"]], ...narrow };
			const query = Object.entries(where).map(([field, value]) => `${field}=${encodeURIComponent(JSON.stringify(value))}`).join("&");
			return `<a href="/desk/task?${query}">${shown}</a>`;
		}
		return shown;
	},
};
