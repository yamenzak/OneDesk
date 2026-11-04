"""A file its app rewrites in place by disk path stays on disk."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree


def test_erpnexts_revaluation_file_stays_on_disk():
	"""ERPNext rewrites a stock revaluation's working file with
	open(file.get_full_path(), "wb"); on R2 that path is a URL and every
	back-dated stock change failed (until 5 November 2026)."""
	store = (tree.APP / "one_storage" / "store.py").read_text(encoding="utf-8")
	assert '("Repost Item Valuation", "reposting_data_file")' in store.split("IN_PLACE = ", 1)[1].split("\n", 1)[0]
	write = store.split("\ndef write(", 1)[1].split("\ndef ", 1)[0]
	assert "in IN_PLACE" in write and write.index("in IN_PLACE") < write.index("put(")
