"""OnePortal's place in One (docs/run/RUN.md, OneRegistry)."""

from onedesk.one.registry.model import App, Settle, _lt

APP = App(
	id="one_portal",
	name="OnePortal",
	kind="app",
	module="One Portal",
	ui="bespoke",
	line=_lt("Let customers and suppliers sign in to see their quotes, orders and invoices, and answer them."),
	pitch=_lt("{one_portal} lets customers and suppliers see their own records without being people in the workspace. They sign in to an account, or open a link to one record, and see their quotes, orders and invoices."),
	brings=(
		_lt("Accounts for customers and suppliers"),
		_lt("A link to one record"),
		_lt("Quotes and invoices answered"),
		_lt("Only their own records"),
	),
	media=("customer-home.webp", "invoices.webp", "supplier-home.webp"),
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
