"""The setup wizard's steps and what each keeps (one_admin/wizard.py):
their order, how an answer joins those kept, which events are noted, and
how far a signup got. Pure, so the tests and OneAdmin's Home read it
without a site."""

from onedesk.one import setup_answers
from onedesk.one.registry.model import _lt

BEFORE = ("you", "company", "language", "field", "companies", "apps", "plan", "region", "payment")
"""The steps before payment, in order."""
AFTER = ("week", "steps", "people")
"""The steps while the workspace is built: `steps` is every app's own,
each noted as `steps:<app>.<key>`."""
STEPS = (*BEFORE, *AFTER)

LABELS = {
	"you": _lt("You"),
	"company": _lt("Company"),
	"language": _lt("Language and Currency"),
	"field": _lt("Field"),
	"companies": _lt("More Companies"),
	"apps": _lt("Apps"),
	"plan": _lt("Plan"),
	"region": _lt("Where Data Is Kept"),
	"payment": _lt("Payment"),
	"week": _lt("Working Week"),
	"steps": _lt("Each App's Setup"),
	"people": _lt("People"),
}

EVENTS = ("Reached", "Finished", "Skipped", "Left")

KEEPS = {
	"you": ("owner",),
	"company": ("companies",),
	"language": ("language", "time_zone", "companies"),
	"field": ("field", "apps"),
	"companies": ("companies",),
	"apps": ("apps",),
	"week": ("working_day",),
	"steps": ("steps",),
	"people": ("people",),
}
"""The answers' keys each step may write; plan, region and payment write
the request's own fields instead."""

OWNER = ("first_name", "last_name")
"""What the wizard takes of the owner: the address is the request's, and a
password is never given here."""

MOST_COMPANIES = 10
MOST_PEOPLE = 100


class Refused(ValueError):
	"""An answer the wizard can't keep; the message says why."""


def kind(step: str) -> str:
	"""The step a noted step is: an app's own (`steps:one_mail.domains`)
	is `steps`. Refused for a step the wizard has not."""
	found, _, own = (step or "").partition(":")
	if found not in STEPS or (found == "steps") != bool(own):
		raise Refused(f"{step!r} is not a step")
	return found


def merge(held: dict, step: str, said: dict, paid: bool) -> dict:
	"""The answers kept once a step's are taken: only the keys that step
	writes, an app's steps one by one, and nothing before payment changed
	once paid. Checked as answers kept part way (setup_answers.check)."""
	at = kind(step)
	if paid and at in BEFORE:
		raise Refused(f"{step} was answered before payment")
	said = said or {}
	unknown = [key for key in said if key not in KEEPS.get(at, ())]
	if unknown:
		raise Refused(f"{step} does not answer {unknown[0]}")
	kept = {**held}
	for key, value in said.items():
		if key == "owner":
			value = {**(held.get("owner") or {}), **{name: value.get(name) for name in OWNER if name in (value or {})}}
		elif key == "steps" and isinstance(value, dict):
			before = held.get("steps") or {}
			value = {**before, **{app: {**(before.get(app) or {}), **given} if isinstance(given, dict) else given for app, given in value.items()}}
		kept[key] = value
	if len(kept.get("companies") or []) > MOST_COMPANIES:
		raise Refused(f"at most {MOST_COMPANIES} companies")
	if len(kept.get("people") or []) > MOST_PEOPLE:
		raise Refused(f"at most {MOST_PEOPLE} people")
	return setup_answers.check(kept, partial=True)


def noted(rows: list[dict], step: str, event: str) -> bool:
	"""Whether this event is noted: each event once in a row, and a step
	left only while it is open, reached and not yet finished or skipped."""
	if event not in EVENTS:
		raise Refused(f"{event!r} is not an event")
	kind(step)
	mine = [one["event"] for one in rows if one["step"] == step]
	if mine and mine[-1] == event:
		return False
	if event == "Left":
		return bool(mine) and mine[-1] == "Reached"
	return True


STAGES = (*BEFORE, "paid", *AFTER, "live")
"""How far a signup can get, for OneAdmin's funnel."""
STAGE_LABELS = {**LABELS, "paid": _lt("Paid"), "live": _lt("Live")}


def furthest(rows: list[dict], paid: bool, live: bool) -> int:
	"""The furthest stage a signup reached, as its place in STAGES; -1 for
	none. Paying counts as reaching every step before it. Pure."""
	at = [STAGES.index(kind(one["step"])) for one in rows if one.get("event") == "Reached"]
	if paid:
		at.append(STAGES.index("paid"))
	if live:
		at.append(STAGES.index("live"))
	return max(at, default=-1)


def funnel(signups: list[tuple[list[dict], bool, bool]]) -> list[dict]:
	"""For each stage, how many signups reached it or one after it: where
	people stop. Each signup is its steps, whether paid and whether live.
	Pure."""
	far = [furthest(*one) for one in signups]
	return [{"stage": stage, "signups": sum(1 for one in far if one >= at)} for at, stage in enumerate(STAGES)]


def stopped(signups: list[tuple[list[dict], bool, bool]]) -> list[dict]:
	"""For each step before payment, how many signups not paid for went no
	further. Pure."""
	far = [furthest(*one) for one in signups if not one[1] and not one[2]]
	return [{"stage": stage, "signups": sum(1 for one in far if one == at)} for at, stage in enumerate(BEFORE)]
