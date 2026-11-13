"""OnePortal's place in One (docs/run/RUN.md, OneRegistry)."""

from onedesk.one.registry.model import App, Settle, _lt

APP = App(
	id="one_portal",
	name="OnePortal",
	kind="app",
	module="One Portal",
	line=_lt("Let customers and suppliers sign in to see their quotes, orders and invoices, and answer them."),
	mark="oneportal",
	rail=140,
	sidebar="OnePortal",
	screens="portal",
	names=("one_portal", "oneportal"),
	frontend="portal",
	help=(
		("overview", "globe"),
		("inviting", "user-plus"),
		("links", "link"),
		("what-they-see", "eye"),
		("who-can-do-what", "shield"),
	),
	ready={
		"ready": True,
		"checked": {
			"copy": {"on": "2026-11-07", "commit": "5e04e24b45b0", "by": "Claude, for Yamen"},
			"demo": {"on": "2026-11-07", "commit": "5e04e24b45b0", "by": "Claude, for Yamen"},
			"notifications": {"on": "2026-11-07", "commit": "5e04e24b45b0", "by": "Claude, for Yamen"},
			"interface": {"on": "2026-11-07", "commit": "5e04e24b45b0", "by": "Claude, for Yamen"},
			"legal": {"on": "2026-11-07", "commit": "5e04e24b45b0", "by": "Claude, for Yamen"},
		},
	},
	settle=(
		Settle("portal.settle", install_only=True),
	),
)
