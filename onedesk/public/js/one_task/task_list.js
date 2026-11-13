(() => {
	const DONE = ["Completed", "Cancelled", "Template"];
	const day_of = (value) => {
		const [day, time] = frappe.datetime.convert_to_user_tz(value).split(" ");
		return [day, frappe.datetime.str_to_user(day) + (time && !time.startsWith("00:00") ? ` ${time.slice(0, 5)}` : "")];
	};
	const due = frappe.meta.get_docfield("Task", "exp_end_date");
	if (due)
		due.formatter = (value, df, options, doc) => {
			if (!value) return "";
			const [day, shown] = day_of(value);
			const late = doc && !DONE.includes(doc.status) && day < frappe.datetime.get_today();
			return late ? `<span class="text-danger">${shown}</span>` : shown;
		};
	const starts = frappe.meta.get_docfield("Task", "exp_start_date");
	if (starts) starts.formatter = (value) => (value ? day_of(value)[1] : "");
})();

frappe.listview_settings["Task"] = frappe.listview_settings["Task"] || {};
frappe.listview_settings["Task"].hide_name_column = true;

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
