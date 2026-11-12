"""Updates in the Saturday window, with each app at the commit the gates
passed (one_admin/releases.py)."""

from datetime import datetime, timedelta
from unittest import mock

from onedesk.one_admin import releases, servers, testbed


def test_the_window_is_the_first_saturday_at_least_three_days_away():
	assert releases.window_after(datetime(2026, 11, 8, 12, 0)) == datetime(2026, 11, 14, 1, 0), "Sunday noon: Saturday is six days off"
	assert releases.window_after(datetime(2026, 11, 12, 12, 0)) == datetime(2026, 11, 21, 1, 0), "Thursday noon: this Saturday is under three days off"
	assert releases.window_after(datetime(2026, 11, 11, 1, 0)) == datetime(2026, 11, 14, 1, 0), "exactly three days is enough"


def test_a_workspace_moves_once_it_has_agreed_or_its_30_days_are_up():
	due = datetime(2026, 11, 14, 1, 0)
	assert releases.may_move(False, due, due)
	assert not releases.may_move(True, due, due + timedelta(days=29))
	assert releases.may_move(True, due, due + timedelta(days=30))


def test_a_window_is_the_workspaces_own_day_and_hour():
	assert releases.window_after(datetime(2026, 11, 8, 12, 0), weekday=0, hour=9) == datetime(2026, 11, 16, 9, 0)


def test_new_workspaces_go_on_the_newest_ready_bench():
	rows = [{"bench": "main", "state": "ready"}, {"bench": "r2", "state": "preparing"}]
	assert servers.newest_ready(rows) == "main"
	assert servers.newest_ready([*rows[:1], {"bench": "r2", "state": "ready"}]) == "r2"


def test_update_now_tells_the_box_at_once():
	tenant = mock.MagicMock(server="eu-1", bench="main", site="a.one", status="Live", terms_pending=0, update_moving=0, update_at=datetime(2026, 11, 10, 9, 0), is_test=0)
	row = mock.MagicMock(benches='[{"bench": "main", "state": "ready"}, {"bench": "r2", "state": "ready"}]')
	with (
		mock.patch.object(servers, "row_of", return_value=row),
		mock.patch.object(releases, "now_datetime", return_value=datetime(2026, 11, 10, 9, 0)),
		mock.patch.object(servers, "instruct") as instruct,
	):
		assert releases.update_now(tenant) == {"waiting": True}
	instruct.assert_called_once_with("eu-1", "move", site="a.one", **{"from": "main", "to": "r2"}, quiet=False)


def test_a_test_workspace_is_never_updated_from_here():
	tenant = mock.MagicMock(name="one-4dl-dev", server=None, bench=None, is_test=1)
	with (
		mock.patch.object(servers, "instruct") as instruct,
		mock.patch.dict(testbed.SAID, {"updated": "{0} is a test workspace."}),
		mock.patch.object(releases.frappe, "throw", side_effect=ValueError) as thrown,
	):
		try:
			releases.update_now(tenant)
		except ValueError:
			pass
	thrown.assert_called_once()
	instruct.assert_not_called()
