"""OneTask's place in One (docs/run/RUN.md, OneRegistry)."""

from onedesk.one.registry.model import App, Region, Settle, _lt

APP = App(
	id="one_task",
	name="OneTask",
	kind="app",
	module="One Task",
	ui="mixed",
	regions=(
		Region("page", "timers", "the reader's task timers, the rail's Timers popover on a page for a phone (Timesheet)"),
	),
	line=_lt("Everybody's work in one list, with checklists, due dates and timers."),
	mark="onetask",
	rail=100,
	sidebar="OneTask",
	screens="task",
	names=("one_task", "onetask"),
	help=(
		("overview", "info"),
		("my-tasks", "list-checks"),
		("all-tasks", "circle-check"),
		("a-task", "file-text"),
		("timing", "timer"),
		("repeats-kinds-delays", "repeat"),
		("notifications", "bell"),
		("asking-oneai", "sparkles"),
		("who-can-do-what", "shield"),
		("settings", "settings"),
	),
	ready={
		"ready": True,
	},
	companies=("Task",),
	interface={
		"Task": {
			"fields": {"parent_task": "corner-left-up"},
			"cards": ({"key": "task.due"}, {"key": "task.steps"}, {"key": "task.waits"}, {"key": "task.logged"}),
			"states": {"order": ("Open", "Working", "Pending Review", "Overdue", "Completed"), "hide": ("Template", "Cancelled")},
		},
	},
	settle=(
		Settle("access.settle"),
		Settle("board.settle"),
	),
	makes=(
		"Task",
		"Timesheet",
	),
)
