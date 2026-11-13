"""AccountCenter's place in One (docs/run/RUN.md, OneRegistry)."""

from onedesk.one.registry.model import App

APP = App(
	id="account_center",
	name="AccountCenter",
	kind="centre",
	module="Account Center",
	screens="account",
	names=("account_center", "accountcenter"),
	help=(
		("overview", "info"),
		("your-account", "user"),
		("people-and-devices", "users"),
		("companies", "building-2"),
		("plan-and-credits", "credit-card"),
		("who-can-do-what", "shield"),
	),
	windowless="AccountCenter is a dialog the avatar's menu and links open, so it has no window, foot or settings of its own.",
	ready={
		"ready": True,
	},
	hooks={
		"one_ai_actions": ("agent.ACTIONS",),
	},
	makes=(
		"Account",
		"Item",
		"Purchase Invoice",
		"Supplier",
	),
)
