"""Hours, written the way somebody reads them back."""

from frappe import _
from frappe.utils import format_datetime, get_datetime

#: Same day: the date once, then two clock times. Across days: both in full.
SAME_DAY = "d MMM HH:mm"
CLOCK = "HH:mm"


def before_validate(doc, method=None) -> None:
	for row in doc.time_logs:
		row.one_when = when(row.from_time, row.to_time)


def when(from_time, to_time) -> str:
	"""One row's block, as a person would say it out loud."""
	if not from_time:
		return ""

	starts = get_datetime(from_time)
	if not to_time:
		# The one row the timer may resume, and it says so rather than looking
		# like a block somebody forgot to finish typing.
		return _("{0} – running").format(format_datetime(starts, SAME_DAY))

	ends = get_datetime(to_time)
	if starts.date() == ends.date():
		return f"{format_datetime(starts, SAME_DAY)} – {format_datetime(ends, CLOCK)}"
	return f"{format_datetime(starts, SAME_DAY)} – {format_datetime(ends, SAME_DAY)}"
