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
	},
	settle=(
		Settle("portal.settle", install_only=True),
	),
)
