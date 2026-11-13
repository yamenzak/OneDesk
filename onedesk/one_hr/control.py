"""OneHR's ControlCenter (docs/ONE.md): Holidays, the lists the workspace
keeps its public holidays and weekly days off in (one_hr/holidays.py).
Workspace administrators only."""

from typing import Annotated

import frappe
from frappe import _, _lt

from onedesk.one import roles, tell
from onedesk.one.company import workspace_company
from onedesk.one.sections import as_opened
from onedesk.one.sections import fields as fields_of
from onedesk.one.sections import opened as opened_of

SECTIONS = [("holidays", _lt("Holidays"), "calendar-days")]


@frappe.whitelist()
def load(
	section: Annotated[str, "Which section."],
	record: Annotated[str | None, "The holiday list it is open on, or new."] = None,
) -> dict:
	roles.require()
	if section != "holidays":
		frappe.throw(_("There is no such section."))
	return _holidays(record)


@frappe.whitelist(methods=["POST"])
def save(
	section: Annotated[str, "Which section."],
	values: Annotated[str | dict, "What was changed."],
	opened: Annotated[str | list | None, "The records as the page loaded them: doctype, name and modified."] = None,
	record: Annotated[str | None, "The holiday list it is open on, or new."] = None,
) -> dict:
	roles.require()
	if section != "holidays":
		frappe.throw(_("There is nothing to save here."))
	_hearing(opened)
	record = _save_holidays(record, frappe.parse_json(values) or {}) or record
	frappe.db.commit()
	return {**_holidays(record), "record": record}


def _hearing(opened) -> None:
	"""The records as the page loaded them, for `sections.as_opened`."""
	frappe.flags.one_opened = {f"{one['doctype']}:{one['name']}": one["modified"] for one in frappe.parse_json(opened) or []}


def _holidays(record: str | None = None) -> dict:
	"""One holiday list, as the page edits it: the list in force today unless
	another is asked for (next year's). Its day off, its country and its
	public holidays are the form; the week's days off are made from the day
	off rather than listed (one_hr/holidays.py)."""
	from onedesk.one_hr import holidays

	held = workspace_company()
	now = holidays.in_force(held=held)
	name = record if record and frappe.db.exists("Holiday List", record) else now
	if not name:
		return {"fields": [], "values": {}, "empty": True, "opened": []}
	doc = frappe.get_doc("Holiday List", name)
	public = [one for one in doc.holidays if not one.weekly_off]
	upcoming = [one for one in public if frappe.utils.getdate(one.holiday_date) >= frappe.utils.getdate(frappe.utils.today())]
	off = holidays.days_off(doc)
	fields = [
		{
			"fieldname": "weekly_offs",
			"fieldtype": "MultiCheck",
			"label": _("Days Off Each Week"),
			"columns": 4,
			"sort_options": False,
			"options": [{"label": _(day), "value": day, "checked": day in off} for day in holidays.WEEK],
			"description": _("Every one of these days in the list is a day off. Tick two for a weekend of two days."),
		},
		*fields_of("Holiday List", ("country", "subdivision")),
	]
	for one in fields:
		if one["fieldname"] == "country":
			one.update({"label": _("Country"), "options": holidays.countries(), "description": None})
		elif one["fieldname"] == "subdivision":
			one.update({"label": _("State or Region"), "options": holidays.subdivisions(doc.country) if doc.country else [], "description": _("Some countries have holidays only in part of the country.")})
	fields.append(
		{
			"fieldname": "holidays",
			"fieldtype": "Table",
			"label": _("Public Holidays"),
			"fields": [
				{"fieldname": "holiday_date", "fieldtype": "Date", "label": _("Date"), "in_list_view": 1, "reqd": 1, "columns": 3},
				{"fieldname": "description", "fieldtype": "Data", "label": _("Holiday"), "in_list_view": 1, "reqd": 1, "columns": 7},
			],
		}
	)
	rows = [{"holiday_date": str(one.holiday_date), "description": frappe.utils.strip_html_tags(one.description or "")} for one in public]
	fields[-1]["data"] = [dict(one) for one in rows]
	next_list = holidays.after(name, held)
	return {
		"fields": fields,
		"values": {
			"country": doc.country,
			"subdivision": doc.subdivision,
			"holidays": rows,
		},
		"list": {
			"name": doc.name,
			"from_date": str(doc.from_date),
			"to_date": str(doc.to_date),
			"days_left": frappe.utils.date_diff(doc.to_date, frappe.utils.today()),
			"in_force": name == now,
			"weekly": off,
			"days_off": len(doc.holidays) - len(public),
			"public": len(public),
		},
		"coming": [{"date": str(one.holiday_date), "what": frappe.utils.strip_html_tags(one.description or "")} for one in upcoming[:1]],
		"next": next_list,
		"now": now,
		"elsewhere": holidays.elsewhere(held),
		"opened": opened_of(doc),
	}


def _save_holidays(record: str | None, values: dict) -> str:
	"""The list's day off, country and public holidays, saved against when the
	page loaded it. A new day off remakes the week's days off; the other
	administrators and the HR managers hear what changed."""
	from onedesk.one_hr import holidays

	name = record or holidays.in_force()
	doc = as_opened(frappe.get_doc("Holiday List", name))
	was_off = holidays.days_off(doc)
	was = {str(one.holiday_date): frappe.utils.strip_html_tags(one.description or "") for one in doc.holidays if not one.weekly_off}
	wanted = {}
	for one in values.get("holidays") or []:
		if one.get("holiday_date"):
			wanted[str(frappe.utils.getdate(one["holiday_date"]))] = (one.get("description") or "").strip() or _("Holiday")
	off = [day for day in holidays.WEEK if day in (values["weekly_offs"] if "weekly_offs" in values else was_off)]
	doc.country = values.get("country") or None
	doc.subdivision = (values.get("subdivision") or None) if doc.country else None
	doc.set("holidays", [])
	for day, what in sorted(wanted.items()):
		doc.append("holidays", {"holiday_date": day, "description": what, "weekly_off": 0})
	holidays.set_days_off(doc, off)
	doc.flags.ignore_permissions = True
	doc.save()
	said = []
	if off != was_off:
		said.append(_("the days off each week are now {0}").format(", ".join(_(day) for day in off) or _("none")))
	added = [day for day in wanted if day not in was]
	dropped = [day for day in was if day not in wanted]
	renamed = [day for day in wanted if day in was and was[day] != wanted[day]]
	for label, days, names in (
		(_("added {0}"), added, wanted),
		(_("removed {0}"), dropped, was),
		(_("renamed {0}"), renamed, wanted),
	):
		if days:
			shown = ", ".join(f"{names[day]} ({frappe.utils.formatdate(day)})" for day in sorted(days)[:3])
			more = len(days) - 3
			said.append(label.format(shown + (" " + _("and {0} more").format(more) if more > 0 else "")))
	if said:
		tell.holidays_changed("; ".join(said), doc.name)
	return doc.name
