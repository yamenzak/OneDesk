"""OneCloud's place in One (docs/run/RUN.md, OneRegistry)."""

from onedesk.one.registry.model import App, Settle, _lt

APP = App(
	id="one_storage",
	name="OneCloud",
	kind="app",
	module="One Storage",
	line=_lt("Keep the company's files in one place and share them with anyone, inside or out."),
	mark="onestorage",
	owns=("One Sheet", "One Doc"),
	rail=20,
	sidebar="OneCloud",
	hooks={
		"one_record_tabs": ("namespace.TABS",),
	},
	settle=(
		Settle("store.unlimit"),
	),
)
