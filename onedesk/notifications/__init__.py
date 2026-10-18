"""Every notification and mail One sends, one file each, by module
(README.md beside this).

`TYPES` is what one/notify.py declares: each file read in the one layout
(layout.py), its words translated where they are shown.
"""

from pathlib import Path

from frappe import _lt

from onedesk.notifications import layout

HERE = Path(__file__).resolve().parent


def files() -> list[Path]:
	"""Every notification file, by module and then by name."""
	return sorted(HERE.glob("*/*.md"))


def _translated(one: dict) -> dict:
	for key in layout.WORDS:
		if one.get(key) and not layout.only_slots(one[key]):
			one[key] = _lt(one[key])
	return one


TYPES = [_translated(layout.read(path.read_text(encoding="utf-8"))) for path in files()]
