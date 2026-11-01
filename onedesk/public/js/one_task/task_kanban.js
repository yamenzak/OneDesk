// OneTask's My Tasks and Inbox are frappe's Kanban (one_task/board.py). What
// One adds: each board shows only its reader's tasks (the Inbox, those in no
// project), a bar to add one, and a timer on every task's card.
frappe.provide("onedesk.task_board");

onedesk.task_board.BOARDS = {
	"My Tasks": { inbox: false },
	Inbox: { inbox: true },
};

onedesk.task_board.mine = (page) => page.doctype === "Task" && onedesk.task_board.BOARDS[page.current_board];

(() => {
	const shape = (Page) => {
		if (!Page || Page.prototype.one_task_board) return;
		Page.prototype.one_task_board = true;
		const effective = Page.prototype.get_effective_filters;
		Page.prototype.get_effective_filters = function (extra) {
			const filters = effective.call(this, extra);
			const board = onedesk.task_board.mine(this);
			if (!board) return filters;
			const own = [["Task", "_assign", "like", `%"${frappe.session.user}"%`]];
			if (board.inbox) own.push(["Task", "project", "is", "not set"]);
			return [...filters, ...own];
		};
		const meta = Page.prototype.setup_meta;
		Page.prototype.setup_meta = function (...args) {
			const said = meta.apply(this, args);
			if (onedesk.task_board.mine(this)) this.page.set_title(__(this.current_board), null, true);
			onedesk.task_board.adder(this);
			return said;
		};
	};
	onedesk.interface.when(frappe.views, "KanbanV2Page", shape);
})();

// A task's subject and when it is due, added on Enter, as the window's own
// command after Add Task (or over the board where there is no window). A task
// in no project is its maker's (one_task/capture.py), so it lands on both.
onedesk.task_board.adder = (page) => {
	if (!page.$one_add) {
		page.$one_add = $(`<div class="one-task-add" data-tour="onetask-add"></div>`);
		const win = page.page && page.page.interface;
		if (win) win.view({ commands: page.$one_add });
		else page.$one_add.insertBefore(page.$container);
		const subject = frappe.ui.form.make_control({
			parent: $(`<div class="one-task-subject"></div>`).appendTo(page.$one_add),
			df: { fieldtype: "Data", fieldname: "subject", placeholder: __("Add a task"), length: 140 },
			render_input: true,
		});
		const due = frappe.ui.form.make_control({
			parent: $(`<div class="one-task-due"></div>`).appendTo(page.$one_add),
			df: { fieldtype: "Date", fieldname: "exp_end_date", placeholder: __("Expected End Date") },
			render_input: true,
		});
		subject.$input.attr("aria-label", __("Add a task")).on("keydown", async (event) => {
			if (event.key !== "Enter") return;
			event.preventDefault();
			const said = (subject.get_value() || "").trim();
			if (!said || subject.$input.prop("disabled")) return;
			subject.$input.prop("disabled", true);
			try {
				await frappe.db.insert({ doctype: "Task", subject: said, exp_end_date: due.get_value() || null });
				subject.set_value("");
				due.set_value("");
				page.board && page.board.refresh();
			} finally {
				subject.$input.prop("disabled", false).trigger("focus");
			}
		});
	}
	page.$one_add.toggle(!!onedesk.task_board.mine(page) && frappe.model.can_create("Task"));
	if (onedesk.task_board.mine(page)) page.$container.attr("data-tour", "onetask-list");
	else if (page.$container.attr("data-tour") === "onetask-list") page.$container.removeAttr("data-tour");
};

// A task's timer on its card: start it, or stop the one running, as the
// rail's Timers does. Only for whoever may keep a timesheet.
onedesk.task_board.running = null;

onedesk.task_board.timer = (card) => {
	const on = () => onedesk.task_board.running && onedesk.task_board.running.task === card.name;
	const $button = frappe.ui.button({
		icon: on() ? "square" : "play",
		variant: "ghost",
		size: "sm",
		title: on() ? __("Stop Timer") : __("Start Timer"),
		css_class: "one-task-timer ms-auto",
		onclick: async (event) => {
			event.stopPropagation();
			if (on()) {
				const logged = await frappe.xcall("onedesk.one_task.timer.stop");
				onedesk.task_timer && onedesk.task_timer.stopped && onedesk.task_timer.stopped(logged);
				onedesk.task_board.running = null;
			} else {
				onedesk.task_board.running = await frappe.xcall("onedesk.one_task.timer.start", { task: card.name });
			}
			$(".one-task-timer").each((_, el) => onedesk.task_board.redraw(el));
		},
	});
	$button.attr({ "data-task": card.name, "aria-label": on() ? __("Stop Timer") : __("Start Timer") });
	$button.on("pointerdown mousedown", (event) => event.stopPropagation());
	return $button;
};

onedesk.task_board.redraw = (el) => {
	const name = el.dataset.task;
	const on = onedesk.task_board.running && onedesk.task_board.running.task === name;
	const label = on ? __("Stop Timer") : __("Start Timer");
	$(el).attr({ title: label, "aria-label": label }).find("svg use").attr("href", `#icon-${on ? "square" : "play"}`);
};

frappe.kanban_v2.extend_settings("Task", {
	renderCard(card, el, ctx, page) {
		page.render_card(card, el);
		if (!frappe.model.can_create("Timesheet")) return;
		if (!page.one_timer_asked) {
			page.one_timer_asked = frappe.xcall("onedesk.one_task.timer.running").then((running) => {
				onedesk.task_board.running = running;
				$(".one-task-timer").each((_, one) => onedesk.task_board.redraw(one));
			});
		}
		const foot = el.lastElementChild && el.lastElementChild.classList.contains("mt-3") ? el.lastElementChild : null;
		const $timer = onedesk.task_board.timer(card);
		if (foot) foot.appendChild($timer[0]);
		else $(`<div class="flex justify-end mt-2"></div>`).append($timer).appendTo(el);
	},
});
