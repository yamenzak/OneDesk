"""Where a backup is kept, and the form a restore streams to Frappe Cloud
(one_admin/backups.py)."""

from onedesk.one_admin import backups


def test_a_part_is_kept_by_where_workspace_day_and_part():
	assert backups.key("daily", "sahara", "2026-11-08", "database", "/x/y/2026-db.sql.gz") == "daily/sahara/2026-11-08/database/2026-db.sql.gz"
	assert backups.key("archived", "sahara", "2026-11-08", "config", None) == "archived/sahara/2026-11-08/config/config"


def test_the_form_is_streamed_with_its_whole_length():
	length, kind, body = backups.form({"key": "uploads/x", "policy": "p"}, "db.sql.gz", 6, iter([b"abc", b"def"]))
	sent = b"".join(body)
	assert len(sent) == length and kind.startswith("multipart/form-data; boundary=one-")
	boundary = kind.split("=", 1)[1]
	assert sent.startswith(f"--{boundary}\r\n".encode()) and sent.endswith(f"\r\n--{boundary}--\r\n".encode())
	assert b'name="key"\r\n\r\nuploads/x\r\n' in sent and b'filename="db.sql.gz"' in sent and b"abcdef" in sent
	assert sent.index(b'name="policy"') < sent.index(b'name="file"'), "S3 reads the fields before the file"
