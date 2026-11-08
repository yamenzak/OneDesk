"""Where a backup is kept, and the form a restore streams to Frappe Cloud
(one_admin/backups.py)."""

from onedesk.one_admin import backups


def test_a_part_is_kept_by_where_workspace_day_and_part():
	assert backups.key("daily", "sahara", "2026-11-08", "database", "/x/y/2026-db.sql.gz") == "daily/sahara/2026-11-08/database/2026-db.sql.gz"
	assert backups.key("archived", "sahara", "2026-11-08", "config", None) == "archived/sahara/2026-11-08/config/config"
