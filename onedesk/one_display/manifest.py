"""OneDisplay's place in One (docs/run/RUN.md, OneRegistry)."""

from onedesk.one.registry.model import App

APP = App(
	id="one_display",
	name="OneDisplay",
	kind="app",
	module="One Display",
	mark="onedisplay",
	rail=130,
	sidebar="OneDisplay",
	screens="display",
	names=("one_display", "onedisplay"),
	help=(
		("overview", "info"),
		("screens-and-pairing", "tv"),
		("templates", "layout-template"),
		("channels", "radio"),
		("slides", "images"),
		("widgets-and-sources", "layout-dashboard"),
		("sound", "speaker"),
		("queues", "list-ordered"),
		("boards", "layout-grid"),
		("alerts", "siren"),
		("notifications", "bell"),
		("asking-oneai", "sparkles"),
		("who-can-do-what", "shield"),
		("settings", "settings"),
	),
	ready={
		"ready": True,
		"checked": {
			"copy": {"on": "2026-11-07", "commit": "70b26c9333b3", "by": "Claude, for Yamen"},
			"demo": {"on": "2026-11-07", "commit": "70b26c9333b3", "by": "Claude, for Yamen"},
			"notifications": {"on": "2026-11-07", "commit": "70b26c9333b3", "by": "Claude, for Yamen"},
			"interface": {"on": "2026-11-07", "commit": "70b26c9333b3", "by": "Claude, for Yamen"},
			"legal": {"on": "2026-11-07", "commit": "70b26c9333b3", "by": "Claude, for Yamen"},
		},
	},
)
