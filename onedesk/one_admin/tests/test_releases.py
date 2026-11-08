"""Updates in the Saturday window, with each app at the commit the gates
passed (one_admin/releases.py)."""

from datetime import datetime

from onedesk.one_admin import releases


def test_the_window_is_the_first_saturday_at_least_three_days_away():
	assert releases.window_after(datetime(2026, 11, 8, 12, 0)) == datetime(2026, 11, 14, 1, 0), "Sunday noon: Saturday is six days off"
	assert releases.window_after(datetime(2026, 11, 12, 12, 0)) == datetime(2026, 11, 21, 1, 0), "Thursday noon: this Saturday is under three days off"
	assert releases.window_after(datetime(2026, 11, 11, 1, 0)) == datetime(2026, 11, 14, 1, 0), "exactly three days is enough"


def test_a_server_is_behind_only_when_onedesk_has_commits_waiting():
	assert releases.behind({"apps": [{"name": "onedesk", "commits_behind": 2}]})
	assert not releases.behind({"apps": [{"name": "onedesk", "commits_behind": 0}, {"name": "frappe", "commits_behind": 9}]})
	assert not releases.behind(None)
