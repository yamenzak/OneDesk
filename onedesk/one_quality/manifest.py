"""OneQuality's place in One (docs/run/RUN.md, OneRegistry)."""

from onedesk.one.registry.model import App, Roles, _lt

APP = App(
	id="one_quality",
	name="OneQuality",
	kind="app",
	module="One Quality",
	line=_lt("Write how work is done, record what went wrong, and follow it until it is fixed."),
	mark="onequality",
	owns=("Quality Management",),
	rail=70,
	sidebar="OneQuality",
	roles=Roles(user=("Quality User",), manager=("Quality Manager",)),
	screens="quality",
	names=("one_quality", "onequality"),
	help=(
		("overview", "info"),
		("procedures-and-goals", "list-ordered"),
		("problems-and-actions", "triangle-alert"),
		("meetings-and-feedback", "users"),
		("notifications", "bell"),
		("asking-oneai", "sparkles"),
		("who-can-do-what", "shield"),
		("settings", "settings"),
	),
	ready={
		"ready": False,
	},
	companies=("Non Conformance", "Quality Action"),
	interface={
		"Non Conformance": {
			"fields": {"subject": "triangle-alert"},
			"cards": ({"key": "quality.nc_actions"}, {"key": "procedure"}, {"key": "quality.raised_by"}),
			"links": (
				{"label": _lt("Quality Action"), "icon": "wrench", "new": "Quality Action", "with": {"one_non_conformance": "name", "procedure": "procedure"}, "when": (("status", "=", "Open"),)},
				{"label": _lt("Quality Action"), "icon": "wrench", "list": "Quality Action", "with": {"one_non_conformance": "name"}},
			),
			"states": {"order": ("Open", "Resolved"), "hide": ("Cancelled",)},
		},
		"Quality Action": {
			"cards": ({"key": "quality.action_done"}, {"key": "quality.action_problem"}, {"key": "goal"}, {"key": "procedure"}),
			"states": {"order": ("Open", "Completed")},
		},
		"Quality Review": {
			"cards": ({"key": "quality.review_met"}, {"key": "procedure"}),
			"states": {"order": ("Open", "Failed", "Passed")},
		},
		"Quality Goal": {
			"cards": ({"key": "quality.goal_last"}, {"key": "procedure"}),
			"states": {"field": "frequency"},
		},
		"Quality Procedure": {
			"cards": ({"key": "quality.procedure_open"}, {"key": "process_owner_full_name"}),
			"states": {"field": "process_owner_full_name"},
		},
		"Quality Meeting": {"states": {"order": ("Open", "Closed")}},
		"Quality Feedback": { "states": {"field": "document_type"}},
	},
)
