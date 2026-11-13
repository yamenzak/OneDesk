"""A change One can't work without, run the old way until the day the
agreements said it takes effect, and the new way from it (docs/READY.md,
mechanism 13). Declared in a module's `trust.py` (`registry.switchover`);
every one is on the Registry page until it is cleaned up. Pure, apart from
`today`."""

import datetime

from . import assemble
from .documents import CHANGES
from .registry import SWITCHOVERS

# How long both ways stay in the code after the new one takes effect: then
# the guard asks for the old way, and the switchover, to go.
CLEAN_DAYS = 30


def _declared(key: str) -> dict:
	assemble._load()
	if key not in SWITCHOVERS:
		raise KeyError(f"There is no switchover {key}.")
	return SWITCHOVERS[key]


def effective(key: str) -> datetime.date:
	"""The day a switchover takes effect: its published change's."""
	one = _declared(key)
	change = next(
		(c for c in CHANGES if c["document"] == one["document"] and c["revision"] == one["revision"]), None
	)
	if not change:
		raise KeyError(f"{key} names {one['document']} {one['revision']}, which is no published change.")
	return datetime.date.fromisoformat(change["effective"])


def _today() -> datetime.date:
	try:
		import frappe

		return frappe.utils.getdate(frappe.utils.nowdate())
	except Exception:
		return datetime.date.today()


def live(key: str, today: datetime.date | None = None) -> bool:
	"""Whether the new way runs: the day has come."""
	return (today or _today()) >= effective(key)


def when(key: str, new, old, *args, **kwargs):
	"""`new(*args, **kwargs)` from the day a switchover takes effect, `old`
	before it: the one way code reaches a switchover's new hosts."""
	return (new if live(key) else old)(*args, **kwargs)


def all_of(today: datetime.date | None = None) -> list[dict]:
	"""Every switchover, with its day and the day it is due to be cleaned up,
	for the Registry page and the guard."""
	assemble._load()
	today = today or _today()
	out = []
	for key, one in SWITCHOVERS.items():
		day = effective(key)
		out.append({**one, "effective": day, "clean_by": day + datetime.timedelta(days=CLEAN_DAYS), "live": today >= day})
	return sorted(out, key=lambda one: one["effective"])
