"""OneCalendar's ControlCenter (docs/ONE.md): Your Calendar Link, the
private address another calendar app subscribes to (one_calendar/feed.py).
For everybody, about their own link only."""

from typing import Annotated

import frappe
from frappe import _


@frappe.whitelist()
def load(
	section: Annotated[str, "Which section."],
	record: Annotated[str | None, "Not used: the link is one page."] = None,
) -> dict:
	if section != "link":
		frappe.throw(_("There is no such section."))
	return _calendar()


def _calendar() -> dict:
	from onedesk.one_calendar import feed

	return {"link": feed.current(), "allowed": feed.allowed()}
