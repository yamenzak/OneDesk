"""Open in OneOS on the workspace: what opens and the two sealed
addresses (one_storage/oneos.py)."""

from onedesk.one_storage import oneos

KEY = b"site-key"


def test_office_files_and_csv_open_and_nothing_else():
	for name in ("Budget.xlsx", "Letter.DOCX", "deck.pptx", "notes.odt", "rows.csv"):
		assert oneos.opens(name), name
	for name in ("photo.jpg", "report.pdf", "README", "", None, "archive.zip"):
		assert not oneos.opens(name), name


def test_an_address_opens_only_its_file_lease_and_use_in_time():
	expires = 2_000_000_000
	sealed = oneos.seal(oneos.UPLOAD, "f1", "lease1", expires, KEY)
	assert oneos.unsealed(oneos.UPLOAD, "f1", "lease1", str(expires), sealed, KEY, expires - 1)
	assert not oneos.unsealed(oneos.DOWNLOAD, "f1", "lease1", str(expires), sealed, KEY, expires - 1), "the download address does not upload"
	assert not oneos.unsealed(oneos.UPLOAD, "f2", "lease1", str(expires), sealed, KEY, expires - 1), "another file"
	assert not oneos.unsealed(oneos.UPLOAD, "f1", "lease2", str(expires), sealed, KEY, expires - 1), "another lease"
	assert not oneos.unsealed(oneos.UPLOAD, "f1", "lease1", str(expires + 1), sealed, KEY, expires - 1), "a later time"
	assert not oneos.unsealed(oneos.UPLOAD, "f1", "lease1", str(expires), sealed, KEY, expires + 1), "run out"
	assert not oneos.unsealed(oneos.UPLOAD, "f1", "lease1", str(expires), sealed, b"other", expires - 1), "another site"
	assert not oneos.unsealed(oneos.UPLOAD, "f1", "lease1", "soon", sealed, KEY, 0)
	assert not oneos.unsealed(oneos.UPLOAD, "f1", "", str(expires), sealed, KEY, 0)
