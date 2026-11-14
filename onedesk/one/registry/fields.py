"""What a company does, the wizard's field question: each field declared
beside the demo company that shows it (one_demo/field.py says what one is,
one_demo/*_field.py holds them), gathered here in the order the wizard asks
(docs/ARC-FIRST-EXPERIENCE.md, Each field has a preset). The wizard presets
its apps and setup answers from here, the answers' `field` is checked
against it (one/setup_answers.py), and a training copy from the demo opens on
its company. Pure."""

from copy import deepcopy

from onedesk.one_demo import clinic_field, consulting_field, making_field, realty_field, trading_field
from onedesk.one_demo.field import EVERY, Field

ORDER = ("clinic", "real_estate", "manufacturer", "trading", "contracting", "services", "retail", "other")
"""The order the wizard offers the fields in."""

_DECLARED = {one.id: one for module in (making_field, clinic_field, realty_field, trading_field, consulting_field) for one in module.FIELDS}

FIELDS: tuple[Field, ...] = tuple(_DECLARED[id] for id in ORDER)

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


def demo(id: str | None) -> str:
	"""The demo company a training copy from the demo opens on for this
	field; Sahara Glass's when the field is not said. Pure."""
	return get(id if id in IDS else "other").demo


def suggested(id: str | None, days_off: list[str] | tuple = ()) -> dict:
	"""The setup answers a field gives a new workspace, its working day with
	the country's days off; nothing when the field is not said. Pure."""
	said = deepcopy(get(id).answers) if id in IDS else {}
	if "working_day" in said:
		said["working_day"]["days_off"] = list(days_off)
	return said


def applied(held: dict, was: str | None, now: str | None, days_off: list[str] | tuple = ()) -> dict:
	"""The answers once the field `was` becomes `now`: what the old field
	gave and the person left as it was is taken away, and what the new one
	gives is added wherever the person has not answered, so their own
	answers win. Pure."""
	before, after = suggested(was, days_off), suggested(now, days_off)
	kept = {**held}
	for key in {*before, *after} - {"steps"}:
		if key in before and kept.get(key) == before[key]:
			kept.pop(key)
		if key in after and not kept.get(key):
			kept[key] = after[key]
	steps = {app: {**given} for app, given in (kept.get("steps") or {}).items()}
	for app, given in (before.get("steps") or {}).items():
		for key, values in given.items():
			if steps.get(app, {}).get(key) == values:
				steps[app].pop(key)
	for app, given in (after.get("steps") or {}).items():
		for key, values in given.items():
			steps.setdefault(app, {}).setdefault(key, values)
	kept.pop("steps", None)
	if any(steps.values()):
		kept["steps"] = {app: given for app, given in steps.items() if given}
	return kept


def unknown(switches) -> list[str]:
	"""The app ids a field names that are not among these switches."""
	return [id for id in (*EVERY, *(id for one in FIELDS for id in one.apps)) if id not in switches]
