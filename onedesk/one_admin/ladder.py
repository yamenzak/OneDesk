"""How far a workspace has fallen, and whether it is time for the next rung.

Nothing of Frappe in here. This is the module that decides when somebody's data
is deleted, so it has to be readable in one sitting and testable in
milliseconds — the same reason `keys.py` and `hosts.py` are pure.

**Five rungs and one direction.** Live, Overdue, Suspended, Archived, Dropped.
Money stops and a workspace walks down them, one at a time, never skipping; the
customer pays and it goes straight back to Live from anywhere above Dropped.
Each rung has a period, and the period is how long the workspace *stays* on that
rung before falling to the next.

**What each rung means, so the periods can be argued about honestly.** Overdue
is nothing at all: the workspace works exactly as it did, and somebody is told.
Suspended is press deactivating the site — it answers a page and nobody can log
in, and the data is untouched. Archived is press destroying the site, having
taken an offsite backup first; our own R2 prefix is not moved, copied or
touched, because it is already ours and already where it should be. Dropped is
the only rung that destroys anything of ours, and it is last on purpose.

**A workspace with no timestamp never falls.** `since` is when it arrived on the
rung it is on, and if we do not know, the answer is to do nothing and let
somebody look. A clock that deletes data on a missing field is a clock that
deletes data on a failed migration.

**A period of zero means never.** Not "immediately". An operator who clears the
grace period is asking for the ladder to stop, not for every overdue workspace
to be suspended tonight, and the reading that loses data is the wrong one.
"""

#: In order, top to bottom. Falling means moving one place to the right.
RUNGS = ("Live", "Overdue", "Suspended", "Archived", "Dropped")

#: The rungs money can be owed on. A workspace here is one somebody should be
#: told about, and the workspace itself is told so its own header can say so.
OWING = ("Overdue", "Suspended", "Archived")

#: The rung a workspace comes back to, whatever it fell to.
PAID = "Live"

#: Default days on each rung before falling off it. Deliberately generous at the
#: top and long at the bottom: the cost of suspending somebody who was going to
#: pay is much higher than the cost of carrying them a week.
DAYS = {"Overdue": 7, "Suspended": 14, "Archived": 30}


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

	A workspace nobody looked at for two months has not earned a jump straight to
	Dropped: each rung does real work — press deactivates, press archives, the
	edge route goes — and skipping one leaves that work undone. So this returns
	them in order and the caller walks them, one a night or all at once.

	The period of each rung is counted from the same `since`, which is the
	conservative reading: a workspace that went Overdue sixty days ago and was
	never touched is Suspended after seven and Archived after fourteen, not
	after twenty-one.
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
