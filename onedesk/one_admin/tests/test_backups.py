"""Where a backup is kept, and the form a restore streams to Frappe Cloud
(one_admin/backups.py)."""

from onedesk.one import backup
from onedesk.one_admin import backups


def test_a_part_is_kept_by_where_workspace_day_and_part():
	assert backups.key("daily", "sahara", "2026-11-08", "database", "/x/y/2026-db.sql.gz") == "daily/sahara/2026-11-08/database/2026-db.sql.gz"
	assert backups.key("archived", "sahara", "2026-11-08", "config", None) == "archived/sahara/2026-11-08/config/config"


def test_a_workspace_keeps_its_turn_and_the_turns_are_spread():
	assert backup.slot("sahara") == backup.slot("sahara")
	slots = {backup.slot(f"workspace-{number}") for number in range(40)}
	assert all(0 <= one < 48 for one in slots)
	assert len(slots) > 15


def test_the_turn_changes_once_in_four_hours_at_the_workspaces_slot():
	start = backup.slot("sahara") * backup.TICK
	assert backup.turn("sahara", start + 4 * 3600) == backup.turn("sahara", start) + 1
	assert backup.turn("sahara", start + 4 * 3600 - 1) == backup.turn("sahara", start)


def test_backups_are_ordered_by_when_they_were_made():
	order = [
		backups.when("recent", "2026-11-09T0415", None),
		backups.when("daily", "2026-11-09", "2026-11-09T01:41:22.000Z"),
		backups.when("recent", "2026-11-09T0015", None),
		backups.when("archived", "2026-11-09", "2026-11-09T22:00:00.000Z"),
		backups.when("daily", "2026-11-08", "2026-11-08T01:41:22.000Z"),
	]
	assert order == sorted(order, reverse=True)
