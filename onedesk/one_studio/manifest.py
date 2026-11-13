"""OneStudio's place in One (docs/run/RUN.md, OneRegistry)."""

from onedesk.one.registry.model import App, Settle, _lt

APP = App(
	id="one_studio",
	name="OneStudio",
	kind="app",
	module="One Studio",
	line=_lt("Shape One to the way you work with your own fields, record types and forms."),
	mark="onestudio",
	rail=160,
	sidebar="OneStudio",
	names=("one_studio", "onestudio"),
	help=(
		("overview", "info"),
		("extensions", "puzzle"),
		("custom-fields", "text-cursor-input"),
		("custom-collections", "database"),
		("numbering", "hash"),
		("printing", "printer"),
		("approvals", "route"),
		("automations", "workflow"),
		("dashboards", "chart-column"),
		("webhooks", "webhook"),
		("notifications", "bell"),
		("asking-oneai", "sparkles"),
		("settings", "settings"),
	),
	no_roles="OneStudio is for the workspace's administrators, whose role is One's, so it ships no roles of its own.",
	hooks={
		"automation_actions": ("automation_steps.TellPeople",),
		"one_record_tabs": ("mend.TABS",),
	},
	settle=(
		Settle("print_blocks.settle"),
		Settle("reports.settle"),
	),
)
