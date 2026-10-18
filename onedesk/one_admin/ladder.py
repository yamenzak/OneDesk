"""How far a workspace has fallen, and whether it is time for the next rung.

Nothing of Frappe in here: this decides when somebody's data is deleted. Five
rungs and one direction; no timestamp never falls; a period of zero means never.
"""

RUNGS = ("Live", "Overdue", "Suspended", "Archived", "Dropped")

OWING = ("Overdue", "Suspended", "Archived")

PAID = "Live"

DAYS = {"Overdue": 7, "Suspended": 14, "Archived": 30}

NOTICE_DAYS = 14


class Unreachable(ValueError):
	"""A rung this workspace cannot get to from where it is."""


def _days(days: dict | None) -> dict:
	"""The periods to use, where an empty table means empty rather than default.

	`days or DAYS` reads an operator who has cleared every period as an operator
	who set none, and hands back the defaults — which is the one misreading here
	that deletes data. Only a missing table falls back.
	"""
	return DAYS if days is None else days


def owing(status: str) -> bool:
	return status in OWING


def below(status: str) -> str | None:
	"""The next rung down, or None at the bottom and off the ladder."""
	if status not in RUNGS:
		return None
	after = RUNGS.index(status) + 1
	if after >= len(RUNGS):
		return None
	return RUNGS[after]


def due(status: str, since, now, days: dict | None = None) -> str | None:
	"""The rung this workspace should be on now, or None to leave it alone.

	`since` and `now` are whatever the caller's clock deals in, as long as
	subtracting them gives something with `.days`. Frappe's datetimes do.
	"""
	rung = below(status)
	if rung is None or since is None or now is None:
		return None

	waited = _days(days).get(status)
	if not waited or waited <= 0:
		return None

	if (now - since).days < waited:
		return None
	return rung


def falls(status: str, since, now, days: dict | None = None) -> list[str]:
	"""Every rung between here and where the clock says it should be.

	In order, for the caller to walk one a night or all at once, never skipping;
	each rung's period is counted from the same `since`.
	"""
	walked = []
	at = status
	while True:
		rung = due(at, since, now, days)
		if rung is None or rung in walked:
			return walked
		walked.append(rung)
		at = rung


def climbing(status: str) -> str:
	"""Where paying puts a workspace, or a refusal.

	Dropped is not a rung anybody climbs off. The site is gone, the files are
	gone, and answering "Live" would be a lie that a screen would then draw.
	"""
	if status == "Dropped":
		raise Unreachable("a dropped workspace cannot be restored — nothing is left of it")
	if status not in RUNGS:
		raise Unreachable(f"{status} is not a rung")
	return PAID


def days_left(status: str, since, now, days: dict | None = None) -> int | None:
	"""How long until the next fall, for the sentence a customer reads.

	None when nothing is going to happen — not on the ladder, no timestamp, or a
	period of zero — which is a different thing from zero days left.
	"""
	if below(status) is None or since is None or now is None:
		return None
	waited = _days(days).get(status)
	if not waited or waited <= 0:
		return None
	return max(0, waited - (now - since).days)
