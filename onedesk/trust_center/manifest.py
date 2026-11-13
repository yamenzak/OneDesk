"""TrustCenter's place in One (docs/run/RUN.md, OneRegistry)."""

from onedesk.one.registry.model import App, Centre, Region, Settle

APP = App(
	id="trust_center",
	name="TrustCenter",
	kind="centre",
	module="Trust Center",
	centre=Centre("trust", "shield-check"),
	ui="bespoke",
	regions=(
		Region("page", "legal", "TrustCenter over the desk: the agreements, the optional services and the companies that receive data"),
	),
	screens="legal",
	names=("trust_center", "trustcenter"),
	help=(
		("overview", "info"),
		("agreeing", "file-check"),
		("optional-services", "toggle-right"),
		("changes", "history"),
		("who-can-do-what", "shield"),
	),
	windowless="TrustCenter is a dialog every module's foot opens, so it has no window, foot or settings of its own.",
	ready={
		"ready": True,
	},
	settle=(
		Settle("gate.told_of_changes"),
	),
)
