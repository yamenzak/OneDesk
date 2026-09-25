"""The week, and the month, in one number each (docs/INTAKE.md §14, §16.9).

**The weekly digest** goes to each person OneAI read for this week, as one
notification that is also mailed when they get mail for notifications: how
many documents arrived, how many OneAI dealt with itself, what still waits
for them, and what falls due in the next seven days. A week with nothing
read for somebody sends them nothing.

**The monthly number** is what a workspace pays OneAI for, said plainly in
Intake Settings: "OneAI handled 1,140 of 1,240 documents this month; 100
needed a person". A document needed a person when OneAI was unsure of what
it read, or proposed something, or was not allowed to do it. A batch scan
counts as the letters cut from it.
"""

import frappe
from frappe import _
from frappe.utils import add_days, get_first_day, getdate, today

from onedesk.one_intake import calendar

def measured(start, end, person: str | None = None) -> dict:
	"""How many documents arrived between two days, and how many of those
	needed a person."""
	conditions = [
		"state = 'Understood'",
		"date(creation) between %(start)s and %(end)s",
		"name not in (select part_of from `tabReading` where ifnull(part_of, '') != '')",
	]
	values = {"start": str(start), "end": str(end)}
	if person:
		conditions.append("on_behalf_of = %(person)s")
		values["person"] = person
	where = " and ".join(conditions)
	arrived = frappe.db.sql(f"select count(*) from `tabReading` where {where}", values)[0][0]
	needed = frappe.db.sql(
		f"""select count(*) from `tabReading` where {where} and (unsure = 1 or name in (
			select reading from `tabIntake Action` where level in ('Proposed', 'Refused')))""",
		values,
	)[0][0]
	return {"arrived": arrived, "needed": needed, "handled": arrived - needed}


def this_month() -> dict:
	return measured(get_first_day(today()), today())


def said(month: dict) -> str:
	"""The monthly number in words."""
	if not month["arrived"]:
		return _("OneAI has read nothing yet this month.")
	return _("OneAI handled {0} of {1} documents this month; {2} needed a person.").format(month["handled"], month["arrived"], month["needed"])


def weekly() -> None:
	"""Scheduler, weekly: one digest per person OneAI read for this week."""
	since, until = add_days(today(), -7), today()
	people = frappe.db.sql_list(
		"""select distinct on_behalf_of from `tabReading`
		where state = 'Understood' and ifnull(on_behalf_of, '') != '' and date(creation) between %s and %s""",
		(str(since), str(until)),
	)
	for person in people:
		try:
			send(person, since, until)
		except Exception:
			frappe.log_error(title=f"Intake digest for {person}")


def send(person: str, since, until) -> None:
	from markupsafe import Markup

	from onedesk.one import notify

	email = frappe.db.get_value("User", {"name": person, "enabled": 1}, "email")
	if not email:
		return
	week = measured(since, until, person)
	if not week["arrived"]:
		return
	lang = frappe.db.get_value("User", person, "language") or frappe.db.get_default("lang") or "en"
	frappe.local.lang = lang
	waiting = frappe.db.sql(
		"""select r.name, r.title from `tabIntake Action` a join `tabReading` r on r.name = a.reading
		where a.level = 'Proposed' and r.on_behalf_of = %s group by r.name order by max(a.creation) desc limit 20""",
		person,
		as_dict=True,
	)
	due = [one for one in calendar.of_readings(add_days(until, 1), add_days(until, 7), everyone=True) if one.get("person") == person]
	notify.notify(
		"Intake Weekly",
		email,
		link="/desk/query-report/Deadlines",
		sender=notify.ONEAI,
		arrived=week["arrived"],
		handled=week["handled"],
		waiting=len(waiting),
		# Built and escaped by body(), in the reader's language.
		week=Markup(body(week, waiting, due)),
	)


def body(week: dict, waiting: list, due: list) -> str:
	esc = frappe.utils.escape_html
	parts = [f"<p>{esc(_('This week {0} documents arrived for you, and OneAI dealt with {1} of them itself.').format(week['arrived'], week['handled']))}</p>"]
	if waiting:
		parts.append(f"<p><b>{esc(_('Waiting for you'))}</b></p><ul>" + "".join(f"<li>{esc(one.title or '')}</li>" for one in waiting) + "</ul>")
	if due:
		parts.append(
			f"<p><b>{esc(_('Due in the next seven days'))}</b></p><ul>"
			+ "".join(f"<li>{esc(frappe.format(getdate(one['date']), 'Date'))} · {esc(one['title'])}</li>" for one in due)
			+ "</ul>"
		)
	return "".join(parts)
