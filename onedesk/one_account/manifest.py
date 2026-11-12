"""OneAccount's place in One (docs/run/RUN.md, OneRegistry)."""

from onedesk.one.registry.model import App

APP = App(
	id="one_account",
	name="OneAccount",
	kind="centre",
	module="One Account",
	mark="oneaccount",
	screens="account",
	names=("one_account", "oneaccount"),
	help=(
		("overview", "info"),
		("your-account", "user"),
		("people-and-devices", "users"),
		("plan-and-credits", "credit-card"),
		("who-can-do-what", "shield"),
	),
	windowless="AccountCenter is a dialog the avatar's menu and links open, so OneAccount has no window, foot or settings of its own.",
	ready={
		"ready": True,
		"checked": {
			"copy": {"on": "2026-11-09", "commit": "ad363dde9810", "by": "Claude, for Yamen"},
			"demo": {"on": "2026-11-09", "commit": "ad363dde9810", "by": "Claude, for Yamen"},
			"notifications": {"on": "2026-11-09", "commit": "ad363dde9810", "by": "Claude, for Yamen"},
			"interface": {"on": "2026-11-09", "commit": "ad363dde9810", "by": "Claude, for Yamen"},
			"legal": {"on": "2026-11-09", "commit": "ad363dde9810", "by": "Claude, for Yamen"},
		},
	},
)
