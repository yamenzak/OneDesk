"""Rua's place in One: its card in Apps, and what of One it stands on
(docs/PRIVATE-APPS.md). Read by the release build and by One, never run."""

from onedesk.one.registry.model import App, Kept, _lt

APP = App(
	id="rua",
	name="Rua",
	kind="app",
	module="Rua",
	line=_lt("Rua Company's setup, and its records brought over from the old Rua app."),
	mark="package",
	needs=("one_book", "one_crm", "one_hr", "one_inventory", "one_project"),
	kept=Kept(_lt("Rua's books, projects and people came over through it.")),
)
