"""The arithmetic of a credit balance, with nothing of Frappe in it.

Same reason as `ladder.py` and `keys.py`: this decides what somebody is allowed
to spend, and a decision that costs money should be readable in milliseconds
against a table of cases rather than against a site.

Three rules, and the second is the one that is easy to get wrong.

**A grant is a bucket with a date on it.** What is left in one is what was
granted plus everything drawn from it, and a bucket whose day has passed stops
counting — which is the whole of expiry. There is no sweep, no expiry row and
nothing to run nightly: a balance simply stops including it.

**The soonest-expiring bucket is drawn first.** The other order loses somebody
credits they paid for while a free monthly grant sits unused beside them, and it
does it quietly, a month later.

**An overdraw belongs to no bucket.** A call the provider answered costs what it
cost, even if it came to more than was held for it, so the arithmetic has to
have somewhere to put that rather than refusing after the money is spent.
"""

from dataclasses import dataclass
from datetime import date

#: Credits are counted to six places. A single call can cost a thousandth of
#: one, and rounding those to zero is a product given away by arithmetic.
PLACES = 6


@dataclass(frozen=True)
class Bucket:
	"""A grant and what is left in it."""

	name: str
	left: float
	#: None never expires. A date is the last day it counts.
	expires_on: date | None = None

	def live_on(self, day: date) -> bool:
		return self.expires_on is None or day <= self.expires_on


@dataclass(frozen=True)
class Draw:
	"""How much of one spend comes out of one bucket.

	`bucket` is None for the part nothing could cover, which is an overdraw and
	is recorded as a spend belonging to no grant.
	"""

	bucket: str | None
	credits: float


def live(buckets: list[Bucket], on: date) -> list[Bucket]:
	"""The buckets that still count, soonest to expire first.

	Ones that never expire go last, because a dated grant is the one somebody
	loses by not spending.
	"""
	return sorted(
		(b for b in buckets if b.live_on(on) and round(b.left, PLACES) > 0),
		key=lambda b: (b.expires_on is None, b.expires_on or date.max, b.name),
	)


def balance(buckets: list[Bucket], on: date, overdrawn: float = 0.0) -> float:
	"""What a workspace has, counting only what has not expired.

	`overdrawn` is the spends that belong to no bucket, which are always
	counted: an overdraw does not expire, because it is money owed rather than
	credit granted.
	"""
	return round(sum(b.left for b in live(buckets, on)) + overdrawn, PLACES)


def draw(buckets: list[Bucket], credits: float, on: date) -> list[Draw]:
	"""Where `credits` comes from, soonest-expiring bucket first.

	A remainder nothing could cover comes back as a `Draw` with no bucket. That
	is not an error here: refusing at this point would mean a call that already
	happened and was never charged for, and the place to refuse is `reserve`,
	before anybody talks to a provider.
	"""
	if credits <= 0:
		return []

	taken, left = [], round(credits, PLACES)
	for bucket in live(buckets, on):
		if left <= 0:
			break
		this = min(bucket.left, left)
		taken.append(Draw(bucket.name, round(this, PLACES)))
		left = round(left - this, PLACES)
	if left > 0:
		taken.append(Draw(None, left))
	return taken


def enough(buckets: list[Bucket], credits: float, held: float, on: date) -> bool:
	"""Whether a workspace can afford one more hold of this size.

	Held credits are subtracted because a reservation is a promise already made.
	Two calls arriving at once both seeing the same balance and both spending it
	is the race this exists to lose.
	"""
	return round(balance(buckets, on) - held - credits, PLACES) >= 0
