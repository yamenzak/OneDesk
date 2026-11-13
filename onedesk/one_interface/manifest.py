"""OneInterface's place in One (docs/run/RUN.md, OneRegistry)."""

from onedesk.one.registry.model import App

APP = App(
	id="one_interface",
	name="OneInterface",
	kind="engine",
	module="One Interface",
	screens="interface",
	names=("one_interface", "oneinterface"),
	help=(
		("overview", "app-window"),
		("records", "file-text"),
		("lists", "list"),
		("dialogs", "square-stack"),
		("looks-and-themes", "palette"),
	),
	windowless="OneInterface is the window every other module is drawn in, so it has no window, foot or settings of its own.",
	no_roles="OneInterface draws every module's screens and keeps no records of its own, so nobody is given it and it ships no roles.",
	ready={
		"ready": False,
	},
)
