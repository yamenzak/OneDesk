"""What OneAI read that belongs on OneCalendar (docs/ARC-AI.md, The agents):
an appointment, as an event for whoever it is for. OneCalendar has no roles
of its own and so no agent: OneProject's coordinator makes it. Pure."""

from onedesk.one_ai.reading.act import Action
from onedesk.one_ai.reading.plans import PERSONAL, real


def event(reading: dict, ctx: dict) -> list[Action]:
	"""An appointment, on the calendar of whoever it is for."""
	if not real(reading, ctx) or reading.get("kind") != "Appointment":
		return []
	when = next((one for one in reading.get("dates") or [] if one.get("what") == "Appointment" and one.get("date")), None)
	if not when:
		return []
	values = {
		"subject": (reading.get("title") or ctx["said"]["appointment"])[:140],
		"starts_on": f"{when['date']} {ctx.get('time_of', {}).get(str(when['date'])) or '09:00:00'}",
		"all_day": 0 if ctx.get("time_of", {}).get(str(when["date"])) else 1,
		"event_type": "Private",
		"description": None if reading.get("sensitivity") in PERSONAL else reading.get("summary"),
		"for": ctx.get("person"),
	}
	return [Action("Create", "Event", values={k: v for k, v in values.items() if v is not None}, key="event", flow="onedesk.one_ai.reading.planning.make_event", sure=True)]
