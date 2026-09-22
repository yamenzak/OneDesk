"""What a call costs, in dollars and then in credits.

Pure, like `prices.py` and `credits.py` on either side of it. This is the
arithmetic between a provider's published rate and a customer's balance, and
every one of its failures is a wrong number rather than an exception — so it is
read back against a table of cases rather than against a site.

**Nothing is estimated.** A `Use` is either a count the provider reported or a
parameter we sent, and it says which. Nothing is derived from the length of a
string, because a token count guessed from characters is a bill guessed from
characters.

**A use with no rate to price it is not free.** It comes back named, and the
caller charges the hold it had already taken rather than charging zero — a call
the provider answered and billed us for is a call somebody has to pay for, and
the alternative is a model that quietly costs money and earns none.

**Nothing converts between units.** A rate and a use meet on `(kind, modality,
unit)` exactly or they do not meet at all; see `prices.py` for why there are ten
units in the catalogue and no arithmetic between them.
"""

from dataclasses import dataclass

#: Credits are counted to six places, the same as the ledger. A single call can
#: cost a thousandth of one.
PLACES = 6

#: Dollars are kept to more, because a provider's rate can be $0.0000528 and a
#: cost rounded to cents before the markup is a cost rounded away entirely.
CENTS = 10

#: What a caller may declare a ceiling on, and the rate each cap is priced
#: against. An action caps what it asks for; it cannot cap what a provider
#: decides to charge, which is what the settle is for.
CAPS = {
	"input_tokens": ("input", "text", "tokens"),
	"cached_tokens": ("cached", "text", "tokens"),
	"output_tokens": ("output", "text", "tokens"),
}


class Unpriceable(Exception):
	"""The operator's own numbers are missing. Said before a call, never after."""


@dataclass(frozen=True)
class Use:
	"""One thing a call consumed, in the provider's own unit."""

	kind: str
	modality: str
	unit: str
	count: float
	#: True when this is a parameter we sent rather than a number the provider
	#: reported. Kept so a bill can say which of its lines were measured.
	asked: bool = False

	@property
	def at(self) -> tuple[str, str, str]:
		return (self.kind, self.modality, self.unit)


@dataclass(frozen=True)
class Bill:
	"""What a call came to, and what nothing could price."""

	usd: float
	credits: float
	lines: tuple[tuple[Use, float], ...] = ()
	#: Uses with no rate to price them. A bill with any of these is not a bill.
	unpriced: tuple[Use, ...] = ()

	@property
	def whole(self) -> bool:
		return not self.unpriced


def cost(rates: list, uses: list[Use]) -> tuple[float, list[Use]]:
	"""What these uses come to in dollars, and which of them nothing could price.

	`rates` are `prices.Rate`s, taken as anything with the same five fields, so
	this module does not have to import the one that reads web pages.
	"""
	by_at = {(r.kind, r.modality, r.unit): r for r in rates}
	total, unpriced = 0.0, []
	for use in uses:
		rate = by_at.get(use.at)
		if rate is None or not rate.per:
			unpriced.append(use)
			continue
		total += (use.count / rate.per) * rate.usd
	return round(total, CENTS), unpriced


def bill(rates: list, uses: list[Use], markup: float, per_dollar: float) -> Bill:
	"""A call's cost to us, marked up, in credits."""
	_configured(markup, per_dollar)
	usd, unpriced = cost(rates, uses)
	lines = []
	for use in uses:
		one, missing = cost(rates, [use])
		lines.append((use, 0.0 if missing else round(one * markup * per_dollar, PLACES)))
	return Bill(
		usd=usd,
		credits=round(usd * markup * per_dollar, PLACES),
		lines=tuple(lines),
		unpriced=tuple(unpriced),
	)


def ceiling(rates: list, caps: dict, markup: float, per_dollar: float) -> Bill:
	"""What the most this call could consume would cost.

	A cap, not a forecast. The point of holding it is that two calls cannot both
	spend the last credit, not that the number is right — the settle replaces it
	with what the provider reported.

	A cap nothing could price is *not* a reason to refuse: an action that caps
	its output tokens against a model priced per picture has simply capped
	something that does not apply. The hold covers what could be priced, and the
	settle is where an unmeterable call is caught.
	"""
	return bill(rates, asked(caps), markup, per_dollar)


def asked(caps: dict) -> list[Use]:
	"""The caps a caller declared, as uses we know the size of."""
	found = []
	for name, count in (caps or {}).items():
		at = CAPS.get(name)
		if not at or not count:
			continue
		kind, modality, unit = at
		found.append(Use(kind=kind, modality=modality, unit=unit, count=float(count), asked=True))
	return found


def _configured(markup: float, per_dollar: float) -> None:
	"""Neither number is guessable from a catalogue.

	Providers publish what a call costs *them*; what it should cost anybody else
	is a decision, and a default here would be us inventing somebody's margin.
	"""
	if not markup or markup <= 0:
		raise Unpriceable("no markup is set for this model or in One Admin Settings")
	if not per_dollar or per_dollar <= 0:
		raise Unpriceable("credits per dollar is not set in One Admin Settings")
