// My Tasks: what is assigned to me and still to do, grouped by when it is due.
//
// The list comes from one_task/mine.py, read as the reader. Adding a task and
// ticking one off go through frappe's own insert and save, so every rule on a
// task — who may change it, ERPNext closing its assignments when it completes,
// one_task/capture.py assigning a new one to its maker — applies here as it
// does on the task's own page.

frappe.pages["my-tasks"].on_page_load = (wrapper) => {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("My Tasks"), single_column: true });
	wrapper.my_tasks = new onedesk.MyTasks(page);
};

frappe.pages["my-tasks"].on_page_show = (wrapper) => {
	wrapper.my_tasks && wrapper.my_tasks.refresh();
};

frappe.provide("onedesk");

onedesk.MyTasks = class MyTasks {
	constructor(page) {
		this.page = page;
		// The list view's own button: same label, same short label, same icon.
		page.set_primary_action(
			{ label: __("Add {0}", [__("Task")]), short_label: __("Add") },
			() => frappe.new_doc("Task"),
			"plus"
		);
		this.$body = $(`<div class="one-tasks">
			<div class="one-tasks-add">
				<div class="one-tasks-subject"></div>
				<div class="one-tasks-due"></div>
			</div>
			<div class="one-tasks-list"></div>
		</div>`).appendTo(page.main);
		const control = (parent, df) =>
			frappe.ui.form.make_control({ parent: this.$body.find(parent), df, render_input: true });
		this.subject = control(".one-tasks-subject", {
			fieldtype: "Data",
			fieldname: "subject",
			placeholder: __("Add a task and press Enter"),
			length: 140,
		});
		this.due = control(".one-tasks-due", { fieldtype: "Date", fieldname: "due", placeholder: __("Due") });
		this.$subject = this.subject.$input;
		this.$subject.on("keydown", (e) => {
			if (e.key === "Enter") {
				e.preventDefault();
				this.add();
			}
		});
		this.$list = this.$body.find(".one-tasks-list");
		this.$list.on("change", ".one-tasks-tick", (e) => this.tick($(e.currentTarget)));
		this.$list.on("click", ".one-tasks-timer", (e) => this.time($(e.currentTarget)));
		// Whoever may keep a timesheet may time a task (one_task/timer.py).
		this.times = frappe.model.can_create("Timesheet");
	}

	async refresh() {
		const [groups, running] = await Promise.all([
			frappe.xcall("onedesk.one_task.mine.tasks"),
			this.times ? frappe.xcall("onedesk.one_task.timer.running") : null,
		]);
		this.running = running;
		this.$list.empty();
		if (!groups.length) {
			this.$list.append(
				frappe.ui.empty_state({
					icon: "list-checks",
					title: __("Nothing is assigned to you."),
					description: __("Add a task above, or ask for one to be assigned to you."),
				})
			);
			return;
		}
		for (const group of groups) {
			const $group = $(`<section class="one-tasks-group">
				<div class="one-tasks-heading text-sm-semibold">${frappe.utils.escape_html(group.label)}
					${frappe.ui.badge.html({ label: String(group.tasks.length), size: "sm" })}</div>
			</section>`).appendTo(this.$list);
			for (const task of group.tasks) $group.append(this.row(task, group.key));
		}
	}

	row(task, group) {
		const pressing = { Urgent: "red", High: "amber" }[task.priority];
		const bits = [];
		if (task.project) {
			bits.push(`<a class="one-tasks-project" href="/desk/project/${encodeURIComponent(task.project)}">${frappe.utils.escape_html(task.project_title)}</a>`);
		}
		if (task.is_milestone) bits.push(`<span>${__("Milestone")}</span>`);
		if (task.due) bits.push(`<span class="${group === "overdue" ? "one-tasks-late" : ""}">${this.day(task.due, group)}</span>`);
		const timing = this.running && this.running.task === task.name;
		const since = timing
			? frappe.ui.badge.html({
					label: __("Since {0}", [moment(this.running.since).format("HH:mm")]),
					theme: "blue",
					size: "sm",
					icon: "timer",
			  })
			: "";
		const timer = this.times
			? frappe.ui.button.html({
					icon: timing ? "square" : "play",
					variant: "ghost",
					size: "sm",
					title: timing ? __("Stop Timer") : __("Start Timer"),
					css_class: "one-tasks-timer",
			  })
			: "";
		return $(`<div class="one-tasks-row" data-name="${frappe.utils.escape_html(task.name)}">
			<input type="checkbox" class="one-tasks-tick" title="${__("Complete")}">
			<a class="one-tasks-title truncate" href="/desk/task/${encodeURIComponent(task.name)}">${frappe.utils.escape_html(task.subject)}</a>
			${pressing ? frappe.ui.badge.html({ label: __(task.priority), theme: pressing, size: "sm" }) : ""}
			${since}
			<span class="one-tasks-about text-sm">${bits.join(`<span class="one-tasks-dot">·</span>`)}</span>
			${timer}
		</div>`);
	}

	// A day in the next week is its weekday; anything else its date. Today and
	// tomorrow are already the group's name.
	day(due, group) {
		if (group === "today" || group === "tomorrow") return "";
		if (group === "week") return moment(due).format("dddd");
		return frappe.datetime.str_to_user(due);
	}

	async add() {
		const subject = (this.subject.get_value() || "").trim();
		if (!subject) return;
		this.$subject.prop("disabled", true);
		try {
			await frappe.db.insert({ doctype: "Task", subject, exp_end_date: this.due.get_value() || null });
			this.subject.set_value("");
			this.due.set_value("");
			await this.refresh();
		} finally {
			this.$subject.prop("disabled", false).trigger("focus");
		}
	}

	// One timer runs at a time; starting this one stops whichever was running.
	async time($button) {
		const name = $button.closest(".one-tasks-row").attr("data-name");
		const timing = this.running && this.running.task === name;
		if (timing) onedesk.task_timer.stopped(await frappe.xcall("onedesk.one_task.timer.stop"));
		else await frappe.xcall("onedesk.one_task.timer.start", { task: name });
		await this.refresh();
	}

	// Ticked stays on the list, struck through, until the page is next opened,
	// so a tick made by mistake is undone where it was made.
	async tick($box) {
		const $row = $box.closest(".one-tasks-row");
		const done = $box.prop("checked");
		$box.prop("disabled", true);
		try {
			await frappe.db.set_value("Task", $row.attr("data-name"), "status", done ? "Completed" : "Open");
			$row.toggleClass("one-tasks-done", done);
		} catch (e) {
			$box.prop("checked", !done);
		} finally {
			$box.prop("disabled", false);
		}
	}
};
