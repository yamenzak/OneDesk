// Who has how many hours of open work in a week (report/workload/workload.py).
// The rows are drawn by an island (frontend/src/workload), modelled on Asana's
// Workload: the team's week in a line with a bar, then a person a row with
// their load as a bar, red past what they have. frappe's grid, its cards and
// its footer stay, out of sight, as the report's own; its filters stay. A
// person's tasks, late tasks and tasks not estimated open their list.
// Everyone on an open project's team is listed, free or not.
const ONE_TASKS = {
	tasks: {},
	late: () => ({ exp_end_date: ["<", frappe.datetime.get_today()] }),
	unestimated: { expected_time: 0 },
};
function one_tasks(user, which) {
	const narrow = typeof ONE_TASKS[which] === "function" ? ONE_TASKS[which]() : ONE_TASKS[which];
	const where = { _assign: ["like", `%${user}%`], status: ["in", ["Open", "Working", "Pending Review"]], ...narrow };
	frappe.route_options = where;
	frappe.set_route("List", "Task");
}

frappe.query_reports["Workload"] = {
	// Drawn again when a task, a timesheet or a leave changes, as a list follows its records.
	onload(report) {
		report.page.wrapper.addClass("one-workload");
		if (report.one_followed) return;
		report.one_followed = true;
		const FOLLOWED = ["Task", "Timesheet", "Leave Application"];
		let soon;
		FOLLOWED.forEach((doctype) => frappe.realtime.doctype_subscribe(doctype));
		frappe.realtime.on("list_update", (data) => {
			if (!FOLLOWED.includes(data.doctype) || frappe.query_report !== report) return;
			clearTimeout(soon);
			soon = setTimeout(() => report.refresh(), 800);
		});
	},
	// The workspace's extensions are told the week as the table shows it
	// (one_studio/places.py), and lent a spot above the rows.
	after_datatable_render() {
		const report = frappe.query_report;
		if (!report) return;
		const props = {
			rows: (report.data || []).filter((one) => one && one.user),
			week: report.raw_data?.message || "",
			onOpen: one_tasks,
		};
		report.$report_message.hide();
		if (report.$one_island && document.contains(report.$one_island[0])) report.one_island.update(props);
		else {
			report.$one_island = $('<div class="one-workload-host"></div>').insertAfter(report.$summary);
			report.one_island = frappe.ui.mount_island("onedesk.workload", report.$one_island[0], props);
		}
		const places = onedesk.places;
		if (!places) return;
		report.$one_spot && report.$one_spot.remove();
		report.$one_spot = null;
		if (!places.listening("oneproject_workload.week")) return;
		const said = report.raw_data || {};
		const week = {
			week: report.get_filter_value("week"),
			project: report.get_filter_value("project") || null,
			said: said.message || "",
			people: (said.result || []).map((one) => ({
				user: one.user,
				name: one.full_name || one.user,
				capacity: one.capacity,
				planned: one.planned,
				free: one.free,
				load: one.load,
				tasks: one.tasks,
				late: one.late,
				not_estimated: one.unestimated,
			})),
		};
		places.emit("oneproject_workload.week", { week }, places.spot(($spot) => {
			report.$one_spot = $spot;
			$spot.addClass("px-5 pt-4").insertBefore(report.$one_island);
		}));
	},
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
