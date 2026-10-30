"""What a call costs, in dollars and then in credits.

Pure, like `credits.py` beside it. Rates come from `one_ai/models.py`.
Nothing is estimated, a use with no rate is not free, and nothing converts
between units.
"""

from dataclasses import dataclass

PLACES = 6

CENTS = 10

CAPS = {
	"input_tokens": ("input", "text", "tokens"),
	"cached_tokens": ("cached", "text", "tokens"),
	"output_tokens": ("output", "text", "tokens"),
	"songs": ("output", "audio", "songs"),
	"video_seconds": ("output", "video", "seconds"),
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
	unpriced: tuple[Use, ...] = ()

	@property
	def whole(self) -> bool:
		return not self.unpriced


def cost(rates: list, uses: list[Use]) -> tuple[float, list[Use]]:
	"""What these uses come to in dollars, and which of them nothing could price.

	`rates` are `one_ai/models.py`'s `Rate`s, or anything with the same five
	fields.
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

	A cap, not a forecast: the settle replaces it with what the provider reported.
	A cap nothing could price is not a reason to refuse.
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
	"""Neither number is guessable from a price list.

	Providers publish what a call costs *them*; what it should cost anybody else
	is a decision, and a default here would be us inventing somebody's margin.
	"""
	if not markup or markup <= 0:
		raise Unpriceable("no markup is set for this model or in OneAdmin Settings")
	if not per_dollar or per_dollar <= 0:
		raise Unpriceable("credits per dollar is not set in OneAdmin Settings")
