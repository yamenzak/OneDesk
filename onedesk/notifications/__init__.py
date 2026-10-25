"""Every notification and mail One sends, one file each, by module
(README.md beside this).

`TYPES` is what one/notify.py declares: each file read in the one layout
(layout.py), its words translated where they are shown.
"""

import importlib
from pathlib import Path

from frappe import _lt, scrub

from onedesk.notifications import layout

HERE = Path(__file__).resolve().parent


def files() -> list[Path]:
	"""Every notification file, by module and then by name."""
	return sorted(HERE.glob("*/*.md"))


def declared() -> list[tuple[str, str, dict]]:
	"""What a module on its way to ready declares in its own notifications.py
	rather than in files here (docs/READY.md, A module's folder): (folder,
	name, type) for each."""
	from onedesk.one import ready

	found = []
	for spec in ready.MODULES.values():
		try:
			module = importlib.import_module(f"onedesk.{spec['folder']}.notifications")
		except ModuleNotFoundError:
			continue
		found += [(spec["folder"], scrub(one["name"]), dict(one)) for one in module.TYPES]
	return found


def _translated(one: dict) -> dict:
	for key in layout.WORDS:
		if one.get(key) and not layout.only_slots(one[key]):
			one[key] = _lt(one[key])
	return one


TYPES = [
	_translated(one)
	for _folder, _name, one in sorted(
		[(path.parent.name, path.stem, layout.read(path.read_text(encoding="utf-8"))) for path in files()] + declared(),
		key=lambda row: (row[0], row[1]),
	)
]
