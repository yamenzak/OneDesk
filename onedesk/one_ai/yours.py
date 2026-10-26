"""What OneAI keeps and reads for the reader, AICenter's Yours: the
memories it keeps, which the reader adds, corrects and forgets, and the
mailboxes and folders reading goes through that are theirs to switch. Also
reading's own settings, which AICenter's Reading draws."""

from typing import Annotated

import frappe
from frappe import _

from onedesk.one import brand, tell
from onedesk.one.sections import as_opened
from onedesk.one.sections import fields as fields_of
from onedesk.one.sections import opened as opened_of


@frappe.whitelist()
def load(
	section: Annotated[str, "Which section: reads."],
	record: Annotated[str | None, "Not used: it is one page."] = None,
) -> dict:
	"""What OneAI Reads, drawn as a centre's section (center_section.js)."""
	if section != "reads":
		frappe.throw(_("There is no such section."))
	return _reads()


INTAKE = ("records", "most_pages", "floor", "audit", "keep_in_place", "quiet_minutes", "household", "submit_einvoices")


NEEDS_AI = ("memory", "oneai")


NEEDS_INTAKE = ("reads", "intake")


def _memory() -> dict:
	"""What OneAI keeps for the reader, with when and the record each is about,
	and what the workspace's administrators wrote down for everybody, which
	OneAI also uses and which the reader can read but not change."""
	rows = frappe.get_all(
		"AI Memory",
		filters={"owner": frappe.session.user},
		fields=["name", "fact", "about_doctype", "about_name", "creation"],
		order_by="creation desc",
		limit=200,
	)
	for one in rows:
		one["about_title"] = _title_of(one.about_doctype, one.about_name)
	knowledge = frappe.get_all(
		"AI Knowledge",
		filters={"enabled": 1},
		fields=["title", "applies_to"],
		order_by="title asc",
		ignore_permissions=True,
	)
	return {
		"facts": rows,
		"knowledge": [{"title": one.title, "applies_to": _(one.applies_to) if one.applies_to else None} for one in knowledge],
	}


def _title_of(doctype: str | None, name: str | None) -> str | None:
	"""A record as a person reads it: its title, or its id where it has none."""
	if not doctype or not name or not frappe.db.exists("DocType", doctype):
		return None
	field = frappe.get_meta(doctype).title_field
	return (frappe.db.get_value(doctype, name, field) if field else None) or name


def _mine(name: str):
	"""One of the reader's own memories. Administrator is not held by the
	doctype's if-owner rule, so the owner is checked here too."""
	doc = frappe.get_doc("AI Memory", name)
	if doc.owner != frappe.session.user:
		frappe.throw(_("That is not one of your memories."), frappe.PermissionError)
	return doc


@frappe.whitelist(methods=["POST"])
def keep(
	fact: Annotated[str, "What OneAI should keep in mind."],
	about_doctype: Annotated[str | None, "The type of record it is about."] = None,
	about_name: Annotated[str | None, "That record."] = None,
	name: Annotated[str | None, "The memory to change; empty for a new one."] = None,
) -> dict:
	"""A memory the reader adds or corrects themselves."""
	said = " ".join((fact or "").split())[:500]
	if not said:
		frappe.throw(_("Say what OneAI should keep in mind."))
	about = {"about_doctype": about_doctype or None, "about_name": about_name or None}
	if about["about_doctype"] and about["about_name"] and not frappe.has_permission(about["about_doctype"], "read", doc=about["about_name"]):
		frappe.throw(_("You cannot open that record."), frappe.PermissionError)
	if name:
		doc = _mine(name)
		doc.update({"fact": said, **about})
		doc.save()
	else:
		frappe.get_doc({"doctype": "AI Memory", "fact": said, **about}).insert()
	return _memory()


@frappe.whitelist(methods=["POST"])
def forget(name: Annotated[str, "The AI Memory to forget."]) -> dict:
	"""One thing OneAI remembers about the reader, forgotten."""
	doc = _mine(name)
	doc.check_permission("delete")
	doc.delete()
	return _memory()


@frappe.whitelist(methods=["POST"])
def forget_all() -> dict:
	"""Everything OneAI remembers about the reader, forgotten."""
	for name in frappe.get_all("AI Memory", filters={"owner": frappe.session.user}, pluck="name"):
		frappe.delete_doc("AI Memory", name)
	return _memory()


def _intake() -> dict:
	"""OneAI's reading settings, with the defaults written in where the record is
	empty (an empty floor is 70%, not nothing), and the month: what arrived,
	what OneAI handled, what needed a person, what was undone, and what waits
	now, for everybody."""
	from onedesk.one_ai.reading import act, pipeline

	doc = frappe.get_single("Reading Settings")
	values = {name: doc.get(name) for name in INTAKE}
	values["most_pages"] = values["most_pages"] or pipeline.MOST_PAGES
	values["floor"] = values["floor"] or act.FLOOR
	fields = [
		{**one, "fieldtype": "Switch"} if one["fieldtype"] == "Check" else one
		for one in fields_of("Reading Settings", INTAKE)
	]
	from onedesk.one_ai.reading import switches

	return {
		"fields": fields,
		"values": values,
		"month": _intake_month(),
		"marks": {app: brand.mark(app) for app in ("OneBook", "OneMail", "OneCloud")},
		**switches.overview(),
		"opened": opened_of(doc),
	}


def _reads() -> dict:
	"""The mailboxes and folders OneAI reads that are the reader's to switch:
	the mailboxes they hold and the folders they may change. Every one of
	them, for an administrator, is AICenter › Reading."""
	from onedesk.one import apps
	from onedesk.one_ai.reading import switches

	if not apps.intake_on():
		return {"off": True}
	return {**switches.overview(mine=True), "marks": {app: brand.mark(app) for app in ("OneMail", "OneCloud")}}


INTAKE_HR = ("one_ai_screen", "one_ai_prepare", "one_ai_transcribe", "one_ai_grievances")


def _intake_month() -> dict:
	from frappe.utils import get_first_day, today

	from onedesk.one_ai.reading import digest, inbox

	month = digest.this_month()
	start = get_first_day(today())
	waiting = frappe.db.sql(f"select count(*) from `tabReading` r where {inbox._box('waiting')}")[0][0]
	undone = frappe.db.count("Reading Action", {"level": "Undone", "modified": [">=", start]})
	return {**month, "waiting": int(waiting or 0), "undone": int(undone or 0)}


TOLD_OF = ("audit", "household", "submit_einvoices", "floor")


def _save_intake(values: dict) -> None:
	from onedesk.one_ai.reading import act

	doc = as_opened(frappe.get_single("Reading Settings"))

	def meant(name):
		value = frappe.utils.flt(doc.get(name))
		return (value or act.FLOOR) if name == "floor" else value

	was = {name: meant(name) for name in TOLD_OF}
	doc.update({name: values[name] for name in INTAKE if name in values})
	doc.save(ignore_permissions=True)
	changed = [name for name in TOLD_OF if was[name] != meant(name)]
	if changed:
		tell.intake_changed(doc, changed)
