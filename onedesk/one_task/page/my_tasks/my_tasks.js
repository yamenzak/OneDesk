// OneTask: the reader's tasks still to do, grouped by when they are due.
//
// Its column is its own navigation, as OneMail's mailboxes and OneCalendar's
// layers are: Add Task, the two views (My Tasks and the Inbox) with how many
// each holds, and at the foot every task as frappe's list and the setup.
//
// The list comes from one_task/mine.py, read as the reader. Adding a task and
// ticking one off go through frappe's own insert and save, so every rule on a
// task — who may change it, ERPNext closing its assignments when it completes,
// one_task/capture.py assigning a new one to its maker — applies here as it
// does on the task's own page.

frappe.pages["my-tasks"].on_page_load = (wrapper) => {
	const page = onedesk.shell.page(wrapper, __("OneTask"), { hide_sidebar: true });
	wrapper.my_tasks = new onedesk.MyTasks(page);
};

frappe.pages["my-tasks"].on_page_show = (wrapper) => {
	wrapper.my_tasks && wrapper.my_tasks.show();
};

frappe.provide("onedesk");

onedesk.MyTasks = class MyTasks {
	// The views, in the column's order: the key is `?section=`, which is also
	// how OneAI knows which is open (oneai.js `where`).
	static VIEWS = [
		{ key: "mine", label: __("My Tasks"), icon: "list-checks", empty: __("No tasks assigned to you"), hint: "" },
		{ key: "inbox", label: __("Inbox"), icon: "inbox", empty: __("No tasks in Inbox"), hint: __("Your own tasks with no project") },
	];

	constructor(page) {
		this.page = page;
		this.view = "mine";
		const panes = onedesk.shell.panes(page.$shell, [{ key: "side", width: 236 }, { key: "list" }]);
		const $side = $(`<div class="one-tasks-side"></div>`)
			.attr({ role: "navigation", "aria-label": __("Views") })
			.appendTo(panes.side);
		frappe.ui
			.button({ label: __("Add Task"), icon: "plus", variant: "solid", css_class: "one-tasks-new", onclick: () => frappe.new_doc("Task") })
			.appendTo($side);
		this.$views = $(`<div class="one-tasks-views"></div>`).appendTo($side);
		this.$views.on("click", "[data-view]", (e) => this.go($(e.currentTarget).attr("data-view")));
		this.draw_foot($(`<div class="one-tasks-foot"></div>`).appendTo($side));

		// The open view: its name, the quick add, then a section per due group.
		const $main = $(`<div class="one-tasks-main">
				<div class="one-tasks-name"></div>
				<div class="one-tasks-add">
					<div class="one-tasks-subject"></div>
					<div class="one-tasks-due"></div>
				</div>
				<div class="one-tasks-list"></div>
			</div>`).appendTo(panes.list);
		const control = (parent, df) => frappe.ui.form.make_control({ parent: $main.find(parent), df, render_input: true });
		this.subject = control(".one-tasks-subject", {
			fieldtype: "Data",
			fieldname: "subject",
			placeholder: __("Add a task"),
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
		this.$name = $main.find(".one-tasks-name");
		this.$list = $main.find(".one-tasks-list");
		this.$list.on("change", ".one-tasks-tick", (e) => this.tick($(e.currentTarget)));
		this.$list.on("click", ".one-tasks-timer", (e) => this.time($(e.currentTarget)));
		// Whoever may keep a timesheet may time a task (one_task/timer.py).
		this.times = frappe.model.can_create("Timesheet");
		this.listen();
	}

	// Every task as frappe's list, and the setup for those who may read it.
	draw_foot($foot) {
		const link = (label, icon, onclick) =>
			frappe.ui.button({ label, icon, variant: "ghost", css_class: "one-tasks-link", onclick }).appendTo($foot);
		link(__("All Tasks"), "circle-check", () => frappe.set_route("List", "Task", { is_template: 0 }));
		if (!frappe.model.can_read("Task Type")) return;
		const $setup = frappe.ui
			.button({ label: __("Setup"), icon: "settings", icon_right: "chevron-down", variant: "ghost", css_class: "one-tasks-link" })
			.appendTo($foot);
		new frappe.ui.Dropdown({
			trigger: $setup,
			side: "top",
			options: [{ label: __("Task Type"), onclick: () => frappe.set_route("List", "Task Type") }],
		});
	}

	// The view the address asks for, drawn again on coming back to the page.
	show() {
		const { section } = frappe.utils.get_query_params();
		this.view = MyTasks.VIEWS.some((one) => one.key === section) ? section : "mine";
		this.refresh();
	}

	go(view) {
		if (view === this.view) return;
		this.view = view;
		history.pushState(null, "", view === "mine" ? location.pathname : `${location.pathname}?section=${view}`);
		this.refresh();
		// An open OneAI panel offers and is told what fits the view now open.
		if (onedesk.oneai && onedesk.oneai.panel) onedesk.oneai.panel.moved(onedesk.oneai.where());
	}

	// Anything about a task that changes elsewhere draws the page again: a task
	// saved, or given to somebody (an assignment is a ToDo), a moment after the
	// last change.
	listen() {
		const doctypes = ["Task", "ToDo"];
		doctypes.forEach((doctype) => frappe.realtime.doctype_subscribe(doctype));
		const again = frappe.utils.debounce(() => this.refresh(), 800);
		frappe.realtime.on("list_update", (data) => {
			if (data && doctypes.includes(data.doctype) && this.$list.is(":visible") && !this.busy) again();
		});
	}

	async refresh() {
		const view = MyTasks.VIEWS.find((one) => one.key === this.view);
		const [groups, running, counts] = await Promise.all([
			frappe.xcall("onedesk.one_task.mine.tasks", { view: this.view }),
			this.times ? frappe.xcall("onedesk.one_task.timer.running") : null,
			frappe.xcall("onedesk.one_task.mine.counts"),
		]);
		this.running = running;
		this.draw_views(counts || {});
		this.$name.text(view.label);
		this.$list.empty();
		this.extended(groups);
		if (!groups.length) {
			this.$list.html(onedesk.shell.empty(view.empty, view.hint, { icon: view.icon }));
			return;
		}
		// A table per due group: frappe's, as every list of records is. The
		// task's name opens it; the tick and the timer act on it where it is.
		this.$list.html(groups.map((group) => `<div class="one-shell-section" data-group="${group.key}"></div>`).join(""));
		for (const group of groups) {
			onedesk.shell.table(this.$list.find(`[data-group="${group.key}"]`), {
				title: `${group.label} · ${group.tasks.length}`,
				rows: group.tasks,
				icon: "list-checks",
				columns: [
					{ label: __("Task"), render: (task) => this.task(task) },
					{ label: __("Project or About"), render: (task) => this.where(task) },
					{
						label: __("Due"),
						render: (task) =>
							task.due ? `<span class="${group.key === "overdue" ? "one-tasks-late" : ""}">${this.day(task.due, group.key)}</span>` : "",
					},
					...(this.times ? [{ label: "", render: (task) => this.timer(task) }] : []),
				],
			});
		}
	}

	// The workspace's extensions on OneTask (one_studio/places.py), told which
	// view is open and what it lists, and lent a note and a button under its
	// name. Drawn again with the view, so nothing they add is there twice.
	extended(groups) {
		this.$name.siblings(".one-place-spot").remove();
		if (!onedesk.places || !onedesk.places.listening("onetask.listed")) return;
		const powers = onedesk.places.spot(($spot) => $spot.insertAfter(this.$name));
		const tasks = (group) =>
			group.tasks.map((one) => ({
				name: one.name,
				subject: one.subject,
				priority: one.priority,
				due: one.due,
				project: one.project,
				project_title: one.project_title,
				is_milestone: !!one.is_milestone,
			}));
		onedesk.places.emit(
			"onetask.listed",
			{ view: this.view, groups: groups.map((group) => ({ key: group.key, label: group.label, tasks: tasks(group) })) },
			powers
		);
	}

	// The column's views, each with how many it holds; My Tasks says how many
	// are late as well.
	draw_views(counts) {
		const esc = frappe.utils.escape_html;
		this.$views.html(
			MyTasks.VIEWS.map((one) => {
				const on = one.key === this.view;
				const late = one.key === "mine" && counts.late ? `<span class="one-tasks-count one-tasks-late" title="${esc(__("Overdue"))}">${counts.late}</span>` : "";
				const count = counts[one.key] ? `<span class="one-tasks-count">${counts[one.key]}</span>` : "";
				return `<button class="one-tasks-view${on ? " one-tasks-on" : ""}" data-view="${one.key}" ${on ? 'aria-current="page"' : ""}>
					${frappe.utils.icon(one.icon, "sm")}<span class="one-tasks-view-label">${esc(one.label)}</span>${late}${count}
				</button>`;
			}).join("")
		);
	}

	// A task's tick, name (which opens it) and how pressing it is.
	task(task) {
		const esc = frappe.utils.escape_html;
		const pressing = { Urgent: "red", High: "amber" }[task.priority];
		const timing = this.running && this.running.task === task.name;
		return `<div class="one-tasks-task" data-name="${esc(task.name)}">
			<input type="checkbox" class="one-tasks-tick" title="${esc(__("Complete"))}">
			<a class="one-tasks-title" href="/desk/task/${encodeURIComponent(task.name)}">${esc(task.subject)}</a>
			${pressing ? frappe.ui.badge.html({ label: __(task.priority), theme: pressing, size: "sm" }) : ""}
			${task.is_milestone ? frappe.ui.badge.html({ label: __("Milestone"), theme: "gray", size: "sm" }) : ""}
			${timing ? frappe.ui.badge.html({ label: __("Since {0}", [moment(this.running.since).format("HH:mm")]), theme: "blue", size: "sm", icon: "timer" }) : ""}
		</div>`;
	}

	// The project a task is in, or, for one in no project, the record it is
	// about (a task OneIntake made about a supplier, say).
	where(task) {
		const esc = frappe.utils.escape_html;
		if (task.project)
			return `<a class="one-tasks-project" href="/desk/project/${encodeURIComponent(task.project)}">${esc(task.project_title)}</a>`;
		if (task.about_title)
			return `<a class="one-tasks-project" href="/desk/${frappe.router.slug(task.one_about_doctype)}/${encodeURIComponent(task.one_about)}" title="${esc(__(task.one_about_doctype))}">${esc(task.about_title)}</a>`;
		return "";
	}

	timer(task) {
		const timing = this.running && this.running.task === task.name;
		return frappe.ui.button.html({
			icon: timing ? "square" : "play",
			variant: "ghost",
			size: "sm",
			title: timing ? __("Stop Timer") : __("Start Timer"),
			css_class: "one-tasks-timer",
			attrs: { "data-name": task.name },
		});
	}

	// Late, how long ago it was due; in the next week, its weekday; anything
	// else its date. Today and tomorrow are already the group's name.
	day(due, group) {
		if (group === "today" || group === "tomorrow") return "";
		if (group === "overdue") return frappe.datetime.prettyDate(due) || frappe.datetime.str_to_user(due);
		if (group === "week") return moment(due).format("dddd");
		return frappe.datetime.str_to_user(due);
	}

	async add() {
		const subject = (this.subject.get_value() || "").trim();
		if (!subject) return;
		this.$subject.prop("disabled", true);
		this.busy = true;
		try {
			await frappe.db.insert({ doctype: "Task", subject, exp_end_date: this.due.get_value() || null });
			this.subject.set_value("");
			this.due.set_value("");
			await this.refresh();
		} finally {
			this.$subject.prop("disabled", false).trigger("focus");
			this.quiet();
		}
	}

	// One timer runs at a time; starting this one stops whichever was running.
	async time($button) {
		const name = $button.attr("data-name");
		const timing = this.running && this.running.task === name;
		if (timing) onedesk.task_timer.stopped(await frappe.xcall("onedesk.one_task.timer.stop"));
		else await frappe.xcall("onedesk.one_task.timer.start", { task: name });
		await this.refresh();
	}

	// Ticked stays on the list, struck through, until the page is next drawn,
	// so a tick made by mistake is undone where it was made.
	async tick($box) {
		const $row = $box.closest(".one-tasks-task");
		const done = $box.prop("checked");
		$box.prop("disabled", true);
		this.busy = true;
		try {
			await frappe.db.set_value("Task", $row.attr("data-name"), "status", done ? "Completed" : "Open");
			$row.toggleClass("one-tasks-done", done);
		} catch (e) {
			$box.prop("checked", !done);
		} finally {
			$box.prop("disabled", false);
			this.quiet();
		}
	}

	// A change made here comes back a moment later as a list_update; it is not
	// heard as somebody else's, or a tick would take its row away at once.
	quiet() {
		clearTimeout(this.quieting);
		this.quieting = setTimeout(() => (this.busy = false), 1500);
	}
};
