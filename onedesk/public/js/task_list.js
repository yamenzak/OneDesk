// A task's due date reads as a day, and red once it has passed on a task still
// to do. ERPNext's Expected End Date is a Datetime, so every list and board
// card said "25-09-2026 00:00:00"; the time is shown only when one was set.
// Lateness is read off the date rather than a status — one_project/board.py says
// why Overdue is not one.
//
// On the docfield rather than the list's formatters, because the board draws
// its cards through frappe.format, which reads `df.formatter` and nothing else.
(() => {
	const DONE = ["Completed", "Cancelled", "Template"];
	const due = frappe.meta.get_docfield("Task", "exp_end_date");
	if (!due) return;
	due.formatter = (value, df, options, doc) => {
		if (!value) return "";
		const [day, time] = frappe.datetime.convert_to_user_tz(value).split(" ");
		const shown = frappe.datetime.str_to_user(day) + (time && !time.startsWith("00:00") ? ` ${time.slice(0, 5)}` : "");
		const late = doc && !DONE.includes(doc.status) && day < frappe.datetime.get_today();
		return late ? `<span class="text-danger">${shown}</span>` : shown;
	};
})();

// On the Gantt, a task with a due date and no start is a day on its due date;
// frappe's view draws a bar from the start and has none to draw. And the view
// mode pills light the first, Hour, whatever the chart is in: frappe-gantt's
// view_is reads a name off options.view_mode, which is a string. Wrapped
// once, for Task only. See one_project/plan.py.
(() => {
	const Gantt = frappe.views.GanttView;
	if (!Gantt || Gantt.prototype.one_due_only) return;
	const prepare = Gantt.prototype.prepare_tasks;
	Gantt.prototype.one_due_only = true;
	Gantt.prototype.prepare_tasks = function () {
		prepare.call(this);
		if (this.doctype !== "Task") return;
		this.tasks = this.tasks
			.map((task) => (task.start ? task : { ...task, start: task.end }))
			.filter((task) => task.start);
	};
	const buttons = Gantt.prototype.setup_view_mode_buttons;
	Gantt.prototype.setup_view_mode_buttons = function () {
		const gantt = this.gantt;
		if (this.doctype === "Task") gantt.view_is = (name) => gantt.config.view_mode.name === name;
		buttons.call(this);
	};
})();
