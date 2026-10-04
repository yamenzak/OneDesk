// Projects on a timeline: frappe's Gantt (and Calendar) view of the Projects
// list, each project a bar from its start to its end, filled as far as it is
// done. A project with only an end is a day on its end; one with neither is
// left off. Its milestones still to come are drawn under it, as rows of their
// own (one_project/tree.py `milestones`), and can't be dragged: a milestone
// is a task, changed on its project's page.
frappe.views.calendar["Project"] = {
	field_map: {
		start: "expected_start_date",
		end: "expected_end_date",
		id: "name",
		title: "project_name",
		progress: "percent_complete",
		// Project has a "Depends on Tasks" tick, which is not a dependency.
		depends_on: null,
		is_milestone: null,
		color: null,
	},
	order_by: "expected_start_date",
};

(() => {
	const Gantt = frappe.views.GanttView;
	if (!Gantt || Gantt.prototype.one_project_timeline) return;
	Gantt.prototype.one_project_timeline = true;
	const render = Gantt.prototype.render;
	Gantt.prototype.render = function () {
		if (this.doctype !== "Project") return render.call(this);
		const projects = this.tasks
			.filter((task) => (this.get_item(task.id) || {}).project_type !== "Employee Boarding")
			.map((task) => (task.start ? task : { ...task, start: task.end }))
			.filter((task) => task.start);
		frappe
			.xcall("onedesk.one_project.tree.milestones", { projects: projects.map((task) => task.id) })
			.then((found) => {
				const under = {};
				for (const one of found || []) (under[one.project] = under[one.project] || []).push(one);
				this.tasks = projects.flatMap((task) => [
					task,
					...(under[task.id] || []).map((one) => ({
						id: one.name,
						name: "◆ " + one.subject,
						start: one.exp_end_date,
						end: one.exp_end_date,
						progress: 0,
						dependencies: "",
						doctype: "Task",
						custom_class: "one-milestone",
					})),
				]);
				render.call(this);
			});
	};
	// frappe-gantt reads the view mode's name off options.view_mode, a string,
	// so the mode pills lit the first one whatever the chart was in.
	const buttons = Gantt.prototype.setup_view_mode_buttons;
	Gantt.prototype.setup_view_mode_buttons = function () {
		const gantt = this.gantt;
		if (this.doctype === "Project") {
			gantt.view_is = (name) => gantt.config.view_mode.name === name;
			// A project runs for weeks; a day per column reads as nothing. Until
			// somebody picks a mode, the timeline opens by the week.
			if (!(this.view_user_settings || {}).gantt_view_mode) gantt.change_view_mode("Week");
		}
		buttons.call(this);
	};
})();
