"""OneStudio's place in One (docs/run/RUN.md, OneRegistry)."""

from onedesk.one.registry.model import App, Settle, _lt

APP = App(
	id="one_studio",
	name="OneStudio",
	kind="app",
	module="One Studio",
	ui="mixed",
	line=_lt("Shape One to the way you work with your own fields, record types and forms."),
	pitch=_lt("{one_studio} is where administrators adapt {one} to the business: the fields a form has, what it checks, and the records no app came with. Describe what you want to {one_ai} and approve the card it makes."),
	brings=(
		_lt("Custom fields and record types"),
		_lt("Numbering, printing and approvals"),
		_lt("Automations and webhooks"),
		_lt("Dashboards"),
	),
	media=("extension.webp", "collection.webp", "numbering.webp"),
	credits=("ai",),
	mark="onestudio",
	rail=160,
	sidebar="OneStudio",
	needs=("one_ai",),
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
