"""Telling people about what OneAI read for them (notifications/one_intake/).

Phishing at once, what waits once the auditor has had its say, a matter that
moved after its task was closed, and the weekly digest.
"""

import frappe

from onedesk.one import notify


def phishing(reading) -> None:
	"""Phishing, said at once to the person OneAI acts for and to whoever put the file there."""
	if reading.verdict != "Phishing":
		return
	people = {reading.on_behalf_of}
	if reading.source_doctype == "File":
		people.add(frappe.db.get_value("File", reading.source_name, "owner"))
	notify.notify(
		"Phishing",
		list(people),
		record=("Reading", reading.name),
		sender=notify.ONEAI,
		dedupe_on=["document_type", "document_name"],
		title=reading.title or "",
	)


def waiting(name: str) -> None:
	"""Something still waits for the person once the auditor has had its say, told once."""
	from onedesk.one_ai.reading.inbox import WAITS

	reading = frappe.db.get_value("Reading", name, ["name", "title", "on_behalf_of", "change"], as_dict=True)
	if not reading or not reading.on_behalf_of or reading.change == "Nothing New":
		return
	waiting = frappe.db.sql(f"select count(*) from `tabReading Action` a where a.reading = %s and {WAITS}", name)[0][0]
	email = frappe.db.get_value("User", reading.on_behalf_of, "email")
	if not waiting or not email:
		return
	notify.notify(
		"Documents Waiting" if waiting > 1 else "Documents Waiting, One Thing",
		email,
		record=("Reading", name),
		link=f"/app/intake?box=waiting&reading={name}",
		sender=notify.ONEAI,
		dedupe_on=["document_type", "document_name"],
		count=waiting,
		title=reading.title or "",
	)


def arrived_after_closing(reading, ctx: dict) -> None:
	"""A matter moved after its task was closed: the task stays closed, and its closer is told."""
	from onedesk.one_hr.hiring import AUTHOR

	held = ctx.get("task")
	if not held or held.status not in ("Completed", "Cancelled") or reading.change in ("Nothing New", "Closing", None):
		return
	closer = held.modified_by
	if not closer or closer == AUTHOR:
		return
	notify.notify(
		"Arrived After Closing",
		closer,
		record=("Task", held.name),
		sender=AUTHOR,
		dedupe_on=["document_type", "document_name", "subject"],
		title=reading.title or "",
	)


def weekly(email: str, week: dict, waiting: list, said: str) -> None:
	"""The weekly digest, to one person, with its body already built."""
	from markupsafe import Markup

	notify.notify(
		"Documents Weekly",
		email,
		link="/desk/query-report/Deadlines",
		sender=notify.ONEAI,
		arrived=week["arrived"],
		handled=week["handled"],
		waiting=len(waiting),
		week=Markup(said),
	)


def couldnt_read(reading, waiting: bool) -> None:
	"""A document OneAI could not read, or waits for credits to read, told once
	to the person it reads for."""
	from frappe import _

	if not reading.on_behalf_of:
		return
	notify.notify(
		"Couldn't Read",
		reading.on_behalf_of,
		record=("Reading", reading.name),
		sender=notify.ONEAI,
		dedupe_on=["document_type", "document_name"],
		title=reading.title or reading.name,
		why=_("The workspace has run out of OneAI credits. It is read as soon as more are added.")
		if waiting
		else _("It failed more than once. Open it to read it yourself, or try again later."),
	)
