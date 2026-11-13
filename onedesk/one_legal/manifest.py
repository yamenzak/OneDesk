"""OneLegal's place in One (docs/run/RUN.md, OneRegistry)."""

from onedesk.one.registry.model import App, Settle

APP = App(
	id="one_legal",
	name="OneLegal",
	kind="centre",
	module="One Legal",
	screens="legal",
	names=("one_legal", "onelegal"),
	help=(
		("overview", "info"),
		("agreeing", "file-check"),
		("optional-services", "toggle-right"),
		("changes", "history"),
		("who-can-do-what", "shield"),
	),
	windowless="TrustCenter is a dialog every module's foot opens, so OneLegal has no window, foot or settings of its own.",
	ready={
		"ready": True,
	},
	settle=(
		Settle("gate.told_of_changes"),
	),
)
