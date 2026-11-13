"""What a company does, the wizard's field question, declared once: each
field's id, what it is called, and the apps it starts with on top of those
every field has (docs/ARC-FIRST-EXPERIENCE.md, The setup wizard). The
wizard presets its apps from here and the answers' `field` is checked
against it (one/setup_answers.py). Pure."""

from dataclasses import dataclass

from onedesk.one.registry.model import _lt

EVERY = ("one_cloud", "one_mail", "one_book", "one_crm", "one_hr", "one_task", "one_calendar", "one_ai")
"""The apps every field starts with."""


@dataclass(frozen=True)
class Field:
	id: str
	label: str
	line: str
	apps: tuple[str, ...] = ()


FIELDS = (
	Field("clinic", _lt("Clinic"), _lt("Patients, appointments and a waiting room."), ("one_inventory", "one_display")),
	Field("real_estate", _lt("Real Estate"), _lt("Properties, owners and tenants."), ("one_portal",)),
	Field("manufacturer", _lt("Manufacturer"), _lt("Makes what it sells, on a shop floor."), ("one_inventory", "one_factory", "one_quality")),
	Field("trading", _lt("Trading"), _lt("Buys and sells goods."), ("one_inventory", "one_portal")),
	Field("contracting", _lt("Contracting"), _lt("Builds or installs on a customer's site."), ("one_project", "one_inventory", "one_quality")),
	Field("services", _lt("Services"), _lt("Sells time and expertise."), ("one_project", "one_portal")),
	Field("retail", _lt("Retail"), _lt("Sells to customers in a shop."), ("one_inventory", "one_display")),
	Field("other", _lt("Other"), _lt("Something else.")),
)

IDS = tuple(one.id for one in FIELDS)


def get(id: str) -> Field:
	for one in FIELDS:
		if one.id == id:
			return one
	raise KeyError(id)


def preset(id: str | None) -> tuple[str, ...]:
	"""The apps a company in this field starts with: every field's, then its
	own; every field's alone when the field is not said. Pure."""
	own = get(id).apps if id in IDS else ()
	return (*EVERY, *(one for one in own if one not in EVERY))


def unknown(switches) -> list[str]:
	"""The app ids a field names that are not among these switches."""
	return [id for id in (*EVERY, *(id for one in FIELDS for id in one.apps)) if id not in switches]
