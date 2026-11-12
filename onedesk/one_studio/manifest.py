"""OneStudio's place in One (docs/run/RUN.md, OneRegistry)."""

from onedesk.one.registry.model import App, _lt

APP = App(
	id="one_studio",
	name="OneStudio",
	kind="app",
	module="One Studio",
	line=_lt("Shape One to the way you work with your own fields, record types and forms."),
	mark="onestudio",
	rail=160,
	sidebar="OneStudio",
)
