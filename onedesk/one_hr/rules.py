"""The arithmetic behind a clock-in, with nothing of Frappe in it.

Addresses, distances and weights are the parts that have to be exactly right
and are miserable to test against a database, so they live here: no `import
frappe`, no site, no session. `tests/test_rules.py` reads this file directly.

Everything above it — reading a Shift Location, writing an attempt, deciding who
may — is in the modules that do import frappe.
"""

import ipaddress
import math

#: Signals, their weight, and the sentence a person reads. A weight is how much
#: confidence the signal takes away, out of a hundred. Nothing here is learned:
#: when a clock-in is refused the screen has to name what was wrong, and a
#: number nobody can explain cannot be named.
#:
#: The dividing line is refuse on what is certain and flag on what is a guess,
#: so the two that are certain — the wrong network, and outside every fence —
#: are weighted to refuse on their own, while everything probabilistic sits
#: under the flag band and needs company to get past it.
SIGNALS = {
	"no-passkey": (100, "No passkey was presented"),
	"passkey-unverified": (100, "The passkey was not unlocked with a face, fingerprint or PIN"),
	"passkey-elsewhere": (25, "Used from a browser unlike the one it was registered on"),
	"device-shared": (40, "Other people have clocked in from this browser today"),
	"network-unknown": (60, "This network has not been seen before"),
	"network-personal": (5, "A network learned from this employee rather than a place"),
	"place-outside": (60, "Outside every place this shift may clock in from"),
	"place-vague": (20, "The position was vaguer than the place it claims"),
	"place-refused": (15, "Location permission was refused"),
	"place-absent": (10, "No position was offered"),
	"travel-impossible": (45, "Too far from the last clock-in for the time between them"),
	"session-elsewhere": (30, "Their desk session is live from a different address"),
	"same-second": (20, "Landed in the same second as somebody else's"),
	"reset-recent": (15, "A second passkey reset within a month"),
	"day-auto-closed": (10, "The day was closed automatically"),
}

#: Below this a clock-in is refused outright; below the second it is written and
#: flagged. Both are overridable per workspace, and both are deliberately far
#: apart: the middle band is where a human looks, and a system with no middle
#: band is one that argues with its own staff at the door.
REFUSE_BELOW = 50
FLAG_BELOW = 85

#: How fast somebody may travel between two clock-ins before the distance stops
#: being possible, in metres per second. 55 is about two hundred kilometres an
#: hour — fast enough that a train or a motorway never trips it, slow enough
#: that two cities in ten minutes does.
TOP_SPEED = 55

#: The earth, for the one formula that needs it.
EARTH_RADIUS = 6_371_000


def confidence(signals) -> int:
	"""A hundred, less what each signal took, floored at nothing.

	Deliberately not multiplicative: two small doubts should read as two small
	doubts rather than compounding into a refusal nobody can account for.
	"""
	lost = sum(SIGNALS.get(name, (0, ""))[0] for name in set(signals))
	return max(0, 100 - lost)


def outcome(score: int, refuse_below: int = REFUSE_BELOW, flag_below: int = FLAG_BELOW) -> str:
	if score < refuse_below:
		return "Refused"
	if score < flag_below:
		return "Flagged"
	return "Allowed"


def says(name: str) -> str:
	return SIGNALS.get(name, (0, name))[1]


def weight(name: str) -> int:
	return SIGNALS.get(name, (0, ""))[0]


def networks(lines) -> list:
	"""Declared addresses, as things an address can be `in`.

	One per line. A line that is neither an address nor a range is dropped
	rather than fatal — the alternative is a typo stopping a whole office
	clocking in, which is a worse failure than a rule one line shorter than
	intended. A bare address is a /32 or /128, which `ip_network` gives for
	free, so nobody has to know that.
	"""
	found = []
	for line in _lines(lines):
		try:
			found.append(ipaddress.ip_network(line, strict=False))
		except ValueError:
			continue
	return found


def address(raw) -> object | None:
	"""What arrived, as something comparable. None when it is not an address."""
	if not raw:
		return None
	try:
		return ipaddress.ip_address(str(raw).strip())
	except ValueError:
		return None


def on_network(raw, lines) -> bool:
	seen = address(raw)
	return bool(seen) and any(seen in one for one in networks(lines))


def distance(lat1, lon1, lat2, lon2) -> float:
	"""Metres between two positions, over a sphere.

	The same haversine HRMS uses, repeated here rather than imported because
	this file may not import anything with a site behind it. It agrees with
	`hrms.hr.utils.get_distance_between_coordinates` to well under a metre,
	which `tests/test_rules.py` checks against a known pair.
	"""
	if None in (lat1, lon1, lat2, lon2):
		return float("inf")

	p1, p2 = math.radians(float(lat1)), math.radians(float(lat2))
	dp = p2 - p1
	dl = math.radians(float(lon2) - float(lon1))
	a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
	return 2 * EARTH_RADIUS * math.asin(math.sqrt(a))


def within(lat, lon, zones) -> dict | None:
	"""The first zone this position is inside, or None.

	A zone is anything with latitude, longitude and radius. Any of them, not
	the nearest: a depot and a site both counting is the point, and the nearest
	is a different question nobody asked.
	"""
	for zone in zones or []:
		radius = float(zone.get("radius") or 0)
		if radius <= 0:
			continue
		if distance(lat, lon, zone.get("latitude"), zone.get("longitude")) <= radius:
			return zone
	return None


def impossible(metres: float, seconds: float) -> bool:
	"""Whether a body could have covered that ground in that time.

	Nothing to say about two clock-ins at the same instant from the same place,
	which is a duplicate rather than a journey.
	"""
	if metres in (None, float("inf")) or seconds is None or seconds < 0:
		return False
	if seconds <= 0:
		return metres > 0
	return metres / seconds > TOP_SPEED


def standing(scores) -> int:
	"""One number for a run of clock-ins, weighted towards the recent ones.

	A linear ramp rather than anything cleverer: the oldest attempt in the
	window counts once and the newest counts as much as the window is long, so
	a bad month three months ago fades without ever being deleted. Given in
	oldest-first order.
	"""
	scores = [int(s) for s in scores or []]
	if not scores:
		return 100
	total = sum(score * (i + 1) for i, score in enumerate(scores))
	return round(total / sum(range(1, len(scores) + 1)))


def enough(votes: int, voters: int, threshold: int) -> bool:
	"""Whether a proposal has been seen often enough by enough people.

	Both, not either: one person clocking in twenty times from their phone's
	hotspot is not a new office, and twenty people passing once through an
	airport is not either.
	"""
	return voters >= threshold and votes >= threshold


def _lines(text) -> list[str]:
	if not text:
		return []
	if isinstance(text, (list, tuple)):
		raw = text
	else:
		raw = str(text).splitlines()
	return [line.strip() for line in raw if line.strip() and not line.strip().startswith("#")]


#: What a mobile browser says about itself. Not a security control — a caller
#: can send any user agent they like — but somebody who forges one to enrol a
#: passkey on the office PC has gone out of their way to weaken their own
#: credential, and the machine they did it on shows up in the ledger anyway.
PHONES = ("iphone", "ipod", "android", "mobi", "windows phone")

#: iPadOS Safari calls itself a Macintosh, so a tablet needs the second check.
TABLETS = ("ipad", "tablet")


def is_phone(agent: str, touch: int = 0) -> bool:
	"""Whether this looks like a device one person carries.

	The touch count is the client's answer to `navigator.maxTouchPoints`, which
	is the only way to tell an iPad from a laptop: since iPadOS 13 the user
	agent of both says Macintosh, and a laptop answers nought.
	"""
	said = (agent or "").lower()
	if any(one in said for one in PHONES + TABLETS):
		return True
	return "macintosh" in said and int(touch or 0) > 1


def device_label(seen) -> str:
	"""What to call a device in a list HR reads.

	The model when the browser gave one, the platform otherwise, and the bare
	word when it gave neither. Never the user agent, which is ninety characters
	of version numbers and says less.
	"""
	seen = seen or {}
	for key in ("model", "platform"):
		said = (seen.get(key) or "").strip()
		if said:
			return said[:60]
	return "Phone"
