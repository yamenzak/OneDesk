"""UpdateCenter's dates (one/update_window.py)."""

from datetime import datetime

from onedesk.one import update_window


def test_an_empty_date_is_none():
	"""An empty Datetime reads back as year 1, which TrustCenter once showed
	as the day the update goes ahead."""
	assert update_window._when(datetime(1, 1, 1)) is None
	assert update_window._when(None) is None
	assert update_window._when(datetime(2026, 11, 21, 1, 0)) == "2026-11-21 01:00:00"
	assert update_window.plainly({"update_held_until": datetime(1, 1, 1)})["held_until"] is None
