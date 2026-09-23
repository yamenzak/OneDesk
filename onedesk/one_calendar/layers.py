"""The calendar's layers, and the one read that merges them.

A layer is one kind of dated thing: your events, your to-dos, your deals' next
steps, who is off. Each module names its own in `hooks.py` under
`one_calendar_layers`, as a list of dicts:

- `key`, `label`, `color` — what the layer is called and drawn in.
- `group` — **Mine** (what is yours) or **Workspace** (what everybody shares).
- `on` — whether it is shown before the reader chooses.
- `doctype` — the record the layer reads, which is also the permission it
  needs: a reader who cannot read Leave Application has no Who's Off layer.
- `rows(start, end)` — a function returning dicts with `name`, `title`,
  `start`, and optionally `end`, `all_day`, `doctype` (when a row opens a
  different record than the layer's), `id` (when one record is on the
  calendar more than once), `editable`, `about` and `description`.

**Nothing is copied.** A layer reads its own records through `frappe.get_list`,
so a deal's next step is on the calendar of whoever may read the deal and of
nobody else, and it moves when the deal does. The only records OneCalendar
owns are Events, which are frappe's own.
"""

from datetime import timedelta
from typing import Annotated

import frappe
from frappe.utils import add_to_date, get_datetime, getdate

#: The most rows one layer hands over for one view.
MOST = 500

#: How long a timed thing with no end is drawn, in minutes.
SPAN = 30


def every() -> list[dict]:
	"""Every layer the modules declare, whether or not the reader may see it."""
	found = []
	for path in frappe.get_hooks("one_calendar_layers") or []:
		found += frappe.get_attr(path)
	return found


def offered() -> list[dict]:
	"""The layers this reader may see, without their functions."""
	return [
		{"key": one["key"], "label": str(one["label"]), "color": one["color"], "group": one["group"], "on": one.get("on", True)}
		for one in every()
		if _may(one)
	]


def _may(layer: dict) -> bool:
	doctype = layer["doctype"]
	return bool(frappe.db.exists("DocType", doctype)) and frappe.has_permission(doctype, "read")


@frappe.whitelist()
@frappe.read_only()
def layers() -> list[dict]:
	return offered()


@frappe.whitelist()
@frappe.read_only()
def entries(
	start: Annotated[str, "The first day shown, as YYYY-MM-DD."],
	end: Annotated[str, "The last day shown, as YYYY-MM-DD."],
	keys: Annotated[str | list | None, "The layers to read; all the reader may see if none."] = None,
) -> list[dict]:
	"""Everything on the calendar between two days, from the layers asked for."""
	wanted = set(frappe.parse_json(keys) or []) if keys else None
	start, end = getdate(start), getdate(end)
	out = []
	for layer in every():
		if wanted is not None and layer["key"] not in wanted:
			continue
		if not _may(layer):
			continue
		for row in frappe.get_attr(layer["rows"])(start, end)[:MOST]:
			out.append(entry(layer, row))
	return out


def entry(layer: dict, row: dict) -> dict:
	"""One row as the calendar draws it. Pure.

	A timed row with no end is drawn SPAN minutes long; an all-day row's end is
	the day after its last, which is how every calendar counts it."""
	all_day = bool(row.get("all_day"))
	start = get_datetime(row["start"])
	end = get_datetime(row["end"]) if row.get("end") else None
	if all_day:
		start = start.replace(hour=0, minute=0, second=0, microsecond=0)
		last = end.date() if end else start.date()
		end = get_datetime(last) + timedelta(days=1)
	elif not end or end <= start:
		end = add_to_date(start, minutes=SPAN)
	doctype = row.get("doctype") or layer["doctype"]
	return {
		"id": f"{layer['key']}:" + (row.get("id") or f"{doctype}:{row['name']}:{start.isoformat()}"),
		"layer": layer["key"],
		"title": row.get("title") or row["name"],
		"start": start.isoformat(),
		"end": end.isoformat(),
		"all_day": all_day,
		"color": layer["color"],
		"doctype": doctype,
		"name": row["name"],
		"editable": bool(row.get("editable")),
		"about": row.get("about"),
		"description": row.get("description"),
	}


def within(field: str, start, end) -> list[list]:
	"""Filters for a Date or Datetime field falling on one of the days shown:
	from the first day to before the day after the last, which reads the same
	for both types."""
	return [[field, ">=", str(start)], [field, "<", str(end + timedelta(days=1))]]


def plain(html, most: int = 140) -> str:
	"""Text out of a rich field, cut to one line's worth."""
	said = " ".join(frappe.utils.strip_html_tags(str(html or "")).split())
	return said if len(said) <= most else said[: most - 1].rsplit(" ", 1)[0] + "…"
