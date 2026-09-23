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
		page.set_primary_action(__("Add Task"), () => frappe.new_doc("Task"));
		this.$body = $(`<div class="one-tasks">
			<form class="one-tasks-add">
				<input type="text" class="form-control one-tasks-subject" maxlength="140">
				<div class="one-tasks-due"></div>
			</form>
			<div class="one-tasks-list"></div>
		</div>`).appendTo(page.main);
		this.$subject = this.$body.find(".one-tasks-subject").attr("placeholder", __("Add a task and press Enter"));
		this.due = frappe.ui.form.make_control({
			parent: this.$body.find(".one-tasks-due"),
			df: { fieldtype: "Date", fieldname: "due", placeholder: __("Due") },
			render_input: true,
		});
		// Enter adds. A form with two fields and no button is never submitted by
		// Enter, so it is listened for rather than left to the browser.
		this.$body.find(".one-tasks-add").on("submit", (e) => e.preventDefault());
		this.$subject.on("keydown", (e) => {
			if (e.key === "Enter") {
				e.preventDefault();
				this.add();
			}
		});
		this.$list = this.$body.find(".one-tasks-list");
		this.$list.on("change", ".one-tasks-tick", (e) => this.tick($(e.currentTarget)));
	}

	async refresh() {
		const groups = await frappe.xcall("onedesk.one_task.mine.tasks");
		this.$list.empty();
		if (!groups.length) {
			this.$list.append(`<div class="one-tasks-empty">${__("Nothing is assigned to you.")}</div>`);
			return;
		}
		for (const group of groups) {
			const $group = $(`<section class="one-tasks-group">
				<h4 class="one-tasks-heading">${frappe.utils.escape_html(group.label)}
					<span class="one-tasks-count">${group.tasks.length}</span></h4>
			</section>`).appendTo(this.$list);
			for (const task of group.tasks) $group.append(this.row(task, group.key));
		}
	}

	row(task, group) {
		const pressing = { Urgent: "red", High: "orange" }[task.priority];
		const bits = [];
		if (task.project) {
			bits.push(`<a class="one-tasks-project" href="/desk/project/${encodeURIComponent(task.project)}">${frappe.utils.escape_html(task.project_title)}</a>`);
		}
		if (task.is_milestone) bits.push(`<span>${__("Milestone")}</span>`);
		if (task.due) bits.push(`<span class="${group === "overdue" ? "one-tasks-late" : ""}">${this.day(task.due, group)}</span>`);
		return $(`<div class="one-tasks-row" data-name="${frappe.utils.escape_html(task.name)}">
			<input type="checkbox" class="one-tasks-tick" title="${__("Complete")}">
			<a class="one-tasks-title" href="/desk/task/${encodeURIComponent(task.name)}">${frappe.utils.escape_html(task.subject)}</a>
			${pressing ? `<span class="indicator-pill ${pressing}">${__(task.priority)}</span>` : ""}
			<span class="one-tasks-about">${bits.join(`<span class="one-tasks-dot">·</span>`)}</span>
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
		const subject = this.$subject.val().trim();
		if (!subject) return;
		this.$subject.prop("disabled", true);
		try {
			await frappe.db.insert({ doctype: "Task", subject, exp_end_date: this.due.get_value() || null });
			this.$subject.val("");
			this.due.set_value("");
			await this.refresh();
		} finally {
			this.$subject.prop("disabled", false).trigger("focus");
		}
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
