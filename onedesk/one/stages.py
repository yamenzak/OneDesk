"""Where a document stands, for a record's head (one/head.py).

A document that moves through stages says where it stands in a sentence and
a track, as Shopify's order page does, and the band keeps only what the form
does not already say. These are the pieces each space's heads build it from:
a step, a track of steps, and the words a sentence is made of.
"""

from frappe import _
from frappe.utils import flt, getdate, today


def step(label: str, state: str, note: str = "") -> dict:
	"""One stage on a track: done, the one it is at (now, or late), or next."""
	return {"label": label, "state": state, "note": note}


def track(*steps, stopped: bool = False) -> dict:
	"""A measure's answer the band draws as a track (band.steps). A step that
	is falsy is a stage this document does not have. On a document `stopped`
	(closed, on hold) nothing is under way, so no step is now or late."""
	kept = [one for one in steps if one]
	if stopped:
		kept = [{**one, "state": "next"} if one["state"] in ("now", "late") else one for one in kept]
	return {"value": "", "steps": kept}


def at(done: bool, started: bool, late: bool = False) -> str:
	return "done" if done else "late" if late else "now" if started else "next"


def days(count: int) -> str:
	return _("1 day") if count == 1 else _("{0} days").format(count)


def overdue(day) -> int:
	"""How many days ago a day passed, or nothing when it has not."""
	return max((getdate(today()) - getdate(day)).days, 0) if day else 0


def share(value) -> str:
	return _("{0}% so far").format(round(flt(value))) if flt(value) else ""


def draft(doc, what: str) -> dict | None:
	"""The sentence of a draft, `what` submitting it does, and of a cancelled
	document; nothing for one that is submitted."""
	if doc.docstatus == 0:
		return {"text": what, "colour": "blue"}
	if doc.docstatus == 2:
		return {"text": _("This document is cancelled."), "colour": "gray"}
	return None
