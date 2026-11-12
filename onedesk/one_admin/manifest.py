"""OneAdmin's place in One (docs/run/RUN.md, OneRegistry)."""

from onedesk.one.registry.model import App, _lt

APP = App(
	id="one_admin",
	name="OneAdmin",
	kind="app",
	module="One Admin",
	mark="oneadmin",
	rail=170,
	sidebar="One Admin",
	screens="admin",
	names=("one_admin", "oneadmin"),
	help=(
		("overview", "info"),
		("workspaces", "building"),
		("settings", "settings"),
	),
	no_roles="OneAdmin runs only on the admin site, where its one role is set, so it ships no roles to a workspace.",
	operators=True,
	interface={
		"Workspace Server": {
			"views": ({"name": "Cards", "label": _lt("Cards View"), "icon": "layout-grid", "island": "onedesk.oneadmin_servers"},),
		},
	},
)
