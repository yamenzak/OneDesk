"""Hours, written the way somebody reads them back.

One thing here is not cosmetic. ERPNext's timer offers to *resume* any row whose
Completed box is unticked and whose From Time is in the past — which is every row
anybody typed by hand, because nothing ticks Completed when you enter a block
yourself. It then counts from that row's From Time, so a 09:00–13:00 block
entered yesterday opens the timer at fifteen and a half hours, and pressing
Complete writes `to_time = now` over the end time that was already there. Four
hours becomes fifteen, silently, on a document payroll reads.

The fix is in `public/js/timesheet.js` and it is small: a row with a To Time is
finished, so the only row the timer may resume is one that has a start and no
end. What is here is the reading half — `one_when` on each row, so the grid says
"21 Sep 09:00 – 13:00" instead of a truncated datetime and a number of hours
with no end beside it.
"""

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
