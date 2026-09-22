"""What a model costs, read off the page its provider publishes.

No frappe in here, on purpose and for the usual reason: this is the module that
decides what a customer is charged, and the way you find out it is wrong is a
margin rather than an error. Text in, rows and gaps out, so it can be read back
in milliseconds against a saved copy of each page.

**There is no single unit and nothing here converts between them.** Workers AI
prices text per million tokens, pictures per 512x512 tile *and* per diffusion
step, speech per audio minute, classification per million images. Gemini prices
everything per million tokens but by modality, and publishes prices that change
on a date. A schema that flattened that to "tokens" would be wrong for half the
catalogue and wrong silently, so a rate keeps the provider's own words for its
unit and the metering code matches on them.

**Nothing has a default.** A fragment this cannot read comes back as a `Gap`
carrying the wording that defeated it, and a model with a gap is not sellable
until a person has looked. A default price is a number we invented and then
billed somebody.
"""

import html
import re
from dataclasses import dataclass, field
from datetime import date

#: What a rate is charged against. `cached` is a read of somebody's context
#: cache and is a third thing, not a cheaper input — the providers price it
#: separately and so do we.
KINDS = ("input", "cached", "output", "usage")

#: Only ever a description. Metering matches on the unit, never on this.
MODALITIES = ("text", "image", "audio", "video", "other")

#: Which modality a unit's own words imply. Order matters: "image MP" is a
#: picture, and "tokens" only means text when nothing more specific said so.
READS_AS = (
	("audio", ("audio", "second", "minute")),
	("video", ("video", "frame")),
	("image", ("tile", "mp", "image", "picture", "step")),
	("text", ("token", "character", "word")),
)

#: The multiplier a provider writes in front of a unit rather than in the
#: number. `M` is Cloudflare's and Google's million; `1k` is Cloudflare's
#: thousand. Anything else is one of whatever it is.
MANY = (
	(1_000_000, ("1m", "m", "million", "1,000,000")),
	(1_000, ("1k", "k", "1,000", "thousand")),
)


@dataclass(frozen=True)
class Rate:
	"""One price, in the provider's own units.

	`per` and `unit` are read together: `per=1_000_000, unit="tokens"` is a
	price for a million tokens and is never divided down, because a provider
	that changes to per-thousand has changed its price and we want to see that
	rather than paper over it.
	"""

	kind: str
	modality: str
	unit: str
	per: int
	usd: float
	#: When the provider says a price takes over from another one. Google
	#: publishes next year's price beside this year's; both are kept and
	#: `in_effect` picks.
	starts: date | None = None
	ends: date | None = None

	def live_on(self, day: date) -> bool:
		return not (self.starts and day < self.starts) and not (self.ends and day > self.ends)


@dataclass(frozen=True)
class Gap:
	"""Something on the page this could not turn into a price."""

	model: str
	what: str
	wording: str


@dataclass
class Read:
	"""Everything one page yielded."""

	rates: dict[str, list[Rate]] = field(default_factory=dict)
	gaps: list[Gap] = field(default_factory=list)

	def priced(self) -> dict[str, list[Rate]]:
		"""Only the models nothing was left unread on."""
		blocked = {gap.model for gap in self.gaps}
		return {name: rows for name, rows in self.rates.items() if name not in blocked and rows}


def in_effect(rates: list[Rate], on: date) -> list[Rate]:
	"""The rates that apply on a given day, one per (kind, modality, unit).

	A provider publishing next year's price is not two prices for one thing; it
	is this year's price and a warning. Charging the wrong side of that date is
	the kind of error nobody notices for a month.
	"""
	best: dict[tuple, Rate] = {}
	for rate in rates:
		if not rate.live_on(on):
			continue
		key = (rate.kind, rate.modality, rate.unit, rate.per)
		held = best.get(key)
		# A dated price beats an undated one: the undated row is the general
		# case and the dated row is the provider being specific.
		if held is None or (rate.starts and not held.starts):
			best[key] = rate
	return list(best.values())


# ---------------------------------------------------------------- reading text


def _plain(fragment: str) -> str:
	return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", fragment))).strip()


def _cells(row: str) -> list[str]:
	return [_plain(c) for c in re.findall(r"(?s)<t[hd][^>]*>(.*?)</t[hd]>", row)]


def _rows(table: str) -> list[list[str]]:
	return [_cells(r) for r in re.findall(r"(?s)<tr[^>]*>(.*?)</tr>", table)]


def _stripped(page: str) -> str:
	return re.sub(r"(?s)<(script|style)\b.*?</\1>", " ", page)


def _money(said: str) -> float | None:
	try:
		return float(said.replace(",", "").replace("$", ""))
	except ValueError:
		return None


def _many(words: list[str]) -> tuple[int, list[str]]:
	"""A leading multiplier, taken off the front of a unit's words."""
	if words:
		first = words[0].lower().strip("$")
		for count, spellings in MANY:
			if first in spellings:
				return count, words[1:]
	return 1, words


def _modality(unit: str) -> str:
	low = unit.lower()
	for modality, words in READS_AS:
		if any(word in low for word in words):
			return modality
	return "other"


# ------------------------------------------------------------- Workers AI


#: A row on Cloudflare's page names a model by its own id, which is what the
#: API answers with too, so nothing has to be matched up by name.
A_WORKERS_MODEL = re.compile(r"^@[a-z0-9]")

#: `$0.027 per M input tokens`, and also `$0.015 per first MP (1024x1024)`.
#: The amount and then everything up to the next amount.
A_PRICE = re.compile(r"\$\s*([\d.,]+)\s*(?:per|/)\s+([^$]+)")

#: The words that say what a price is charged against rather than what of.
SAYS_KIND = (
	("cached", ("cached input", "cached", "context caching", "cache read")),
	("input", ("input",)),
	("output", ("output",)),
)


def workers_ai(page: str) -> Read:
	"""Cloudflare's published Workers AI prices.

	One table, one row per model, and a free-text price cell that may hold one
	price or four in completely different units. The model id is the row's own
	first cell, so there is nothing to match against the API's answer.
	"""
	read = Read()
	for table in re.findall(r"(?s)<table[^>]*>(.*?)</table>", _stripped(page)):
		for cells in _rows(table):
			if len(cells) < 2 or not A_WORKERS_MODEL.match(cells[0]):
				continue
			model, wording = cells[0], cells[1]
			rates, unread = _priced(wording)
			if rates:
				read.rates.setdefault(model, []).extend(rates)
			if unread or not rates:
				read.gaps.append(Gap(model, "price", unread or wording))
	if not read.rates:
		read.gaps.append(Gap("", "page", "no model rows on the page at all"))
	return read


def _priced(wording: str) -> tuple[list[Rate], str]:
	"""Every `$N per <something>` in one cell, and whatever was left over."""
	rates, at = [], 0
	unread = []
	for found in A_PRICE.finditer(wording):
		unread.append(wording[at : found.start()])
		at = found.end()
		usd = _money(found.group(1))
		if usd is None:
			unread.append(found.group(0))
			continue
		rates.append(_rate(usd, found.group(2)))
	unread.append(wording[at:])
	left = " ".join(part.strip() for part in unread if part.strip())
	return rates, left


def _rate(usd: float, said: str) -> Rate:
	"""One `$N per <words>` turned into a rate, keeping the provider's words.

	`per input 512x512 tile, per step` is a real unit on this page, and so is
	`first MP (1024x1024)`. Neither is normalised into anything: the kind words
	come off the front or the back, and what is left is the unit verbatim.
	"""
	low = said.lower()
	kind = "usage"
	for named, spellings in SAYS_KIND:
		if any(spelling in low for spelling in spellings):
			kind = named
			break

	words = said.replace(",", " ").split()
	if kind != "usage":
		named = dict(SAYS_KIND)[kind]
		words = [w for w in words if w.lower() not in ("cached", "input", "output")]
	per, words = _many(words)
	unit = " ".join(words).strip(" .")
	return Rate(kind=kind, modality=_modality(unit), unit=unit, per=per, usd=usd)


# ---------------------------------------------------------------- Gemini


#: Google's page is one table per model per tier, with the model in a heading
#: above the table rather than in a cell of it, so the reading has to be done in
#: document order.
A_HEADING = re.compile(r"(?s)<h([23])[^>]*>(.*?)</h\1>|<table[^>]*>(.*?)</table>")

#: The only tier we sell. Batch, Flex and Priority are different products with
#: different latencies, and offering one would be a decision rather than a price.
SOLD = "Standard"

#: What a row's label means. Longest first, so "Text input price" is not read as
#: the general "Input price".
LABELLED = (
	("text input price", ("input", "text")),
	("image input price", ("input", "image")),
	("audio input price", ("input", "audio")),
	("video input price", ("input", "video")),
	("context caching price", ("cached", "text")),
	("output price", ("output", "text")),
	("input price", ("input", "text")),
)

#: Rows on the page that are not a price per call: a grounding tool, a storage
#: charge per hour, a tuning job, and Google's note about training. Skipped
#: rather than flagged — a model is sellable without them.
NOT_A_CALL = (
	"grounding with",
	"used to improve",
	"tuning price",
	"context caching (storage)",
	"storage price",
)

#: `Paid Tier, per 1M tokens in USD` — where Google puts the unit.
A_UNIT = re.compile(r"per\s+([\d.,]*\s*[a-z]*)\s+([a-z ]+?)(?:\s+in\s+usd)?\s*$", re.I)

#: `$1.50 starting January 1, 2027` and `$0.75 through December 31, 2026`.
A_WHEN = re.compile(r"\b(starting|through|until|from)\s+([A-Z][a-z]+\s+\d{1,2},\s*\d{4})", re.I)

MONTHS = (
	"january", "february", "march", "april", "may", "june",
	"july", "august", "september", "october", "november", "december",
)


def fold(name: str) -> str:
	"""A model's name reduced to something two sources can be compared on.

	Google's price page says "Gemini 3.1 Flash Image (Nano Banana 2)" and its
	API says `gemini-3.1-flash-image`. Neither is going to change to suit us, so
	both go through here: lower case, no punctuation, no parenthetical, single
	hyphens. A name that still does not match is a gap rather than a guess.
	"""
	said = re.sub(r"\([^)]*\)", " ", name)
	said = re.sub(r"[^0-9a-zA-Z]+", "-", said.lower())
	return said.strip("-")


def gemini(page: str) -> Read:
	"""Google's published Gemini prices.

	Read in document order because the model is a heading and the prices are a
	table under it, and only the Standard tier is read because that is the only
	one we sell.
	"""
	read = Read()
	named: list[str] = []
	tier = ""
	for found in A_HEADING.finditer(_stripped(page)):
		if found.group(2) is not None:
			said = _plain(found.group(2))
			if found.group(1) == "2":
				named, tier = _named(said), ""
			else:
				tier = said
			continue
		if not named or (tier and tier != SOLD):
			continue
		for model in named:
			_one_table(read, model, found.group(3))
	if not read.rates:
		read.gaps.append(Gap("", "page", "no priced model tables on the page at all"))
	return read


#: One heading, more than one model. Google prices its three Live models in a
#: single table under a heading that lists them, and the alternative to splitting
#: it is three models nothing could price.
A_LIST = re.compile(r"\s*,\s*and\s+|\s*,\s*|\s+and\s+")


def _named(heading: str) -> list[str]:
	parts = [part.strip() for part in A_LIST.split(heading) if part.strip()]
	return parts or [heading.strip()]


def _one_table(read: Read, model: str, table: str) -> None:
	rows = _rows(table)
	if not rows:
		return
	per, unit = _unit_of(rows[0])
	for cells in rows[1:]:
		if len(cells) < 2:
			continue
		label = cells[0].lower()
		if not label or any(said in label for said in NOT_A_CALL):
			continue
		named = next((k for spelling, k in LABELLED if label.startswith(spelling)), None)
		if named is None:
			continue
		# The paid column is the last one; the free tier is not what we resell.
		paid = cells[-1]
		if not per:
			read.gaps.append(Gap(model, "unit", _plain(" ".join(rows[0])) or "no unit on the table"))
			return
		kind, modality = named
		rates, unread = _dated(paid, kind, modality, per, unit)
		read.rates.setdefault(model, []).extend(rates)
		if unread:
			read.gaps.append(Gap(model, cells[0], unread))


def _unit_of(header: list[str]) -> tuple[int, str]:
	"""`Paid Tier, per 1M tokens in USD` — the multiplier and the noun."""
	for cell in reversed(header):
		found = A_UNIT.search(cell)
		if not found:
			continue
		per, words = _many([found.group(1).strip()] if found.group(1).strip() else [])
		unit = found.group(2).strip()
		if words:
			unit = f"{' '.join(words)} {unit}".strip()
		return per, unit
	return 0, ""


def _dated(paid: str, kind: str, modality: str, per: int, unit: str) -> tuple[list[Rate], str]:
	"""Every amount in the paid cell, in whatever unit it turns out to be in.

	This cell is where Google's page is at its least regular, and all four
	shapes below are real:

	    $0.75 through December 31, 2026. $1.50 starting January 1, 2027.
	    $0.10 (text / image / video) $0.30 (audio)
	    $0.45 ($0.00012 per image)
	    $0.075 ... $0.50 / 1,000,000 tokens per hour (storage price)

	So an amount is read together with what follows it: a date makes it a price
	that takes over on a day, a list of modalities makes it a price for those
	and no others, a unit of its own makes it a rate in that unit rather than
	the table's, and the word storage makes it a different charge sharing a cell
	— which is left unread on purpose, because a per-hour charge billed as a
	per-call one is a customer charged for holding still.
	"""
	if not paid or paid.lower().startswith(("free", "not available", "n/a")):
		return [], ""

	fragments: list[tuple[float, str, bool]] = []
	unread, at = [], 0
	for found in re.finditer(r"\$\s*([\d.,]+)", paid):
		unread.append(paid[at : found.start()])
		usd = _money(found.group(1))
		nxt = paid.find("$", found.end())
		said = paid[found.end() : nxt if nxt != -1 else len(paid)]
		at = nxt if nxt != -1 else len(paid)
		if any(word in said.lower() for word in NOT_A_CALL):
			# A storage charge sharing a cell with a call price. Skipped rather
			# than left unread: a model is perfectly sellable without it, and
			# flagging it would put every cached-input model in front of a
			# person for a line that is not a per-call price at all.
			continue
		if usd is None:
			unread.append(found.group(0) + said)
			continue

		# An amount's own unit is only believed when the page attaches it to the
		# amount — `$0.005/min`, or a parenthetical opened just before it as in
		# `$0.45 ($0.00012 per image)`. Read loosely, the same pattern picks up
		# prose like "Equivalent to $0.045 per 0.5K image", where 1K is a
		# picture's width and not a thousand of anything; reading that as a
		# multiplier is a bill a thousand times too large.
		attached = said.startswith("/") or paid[: found.start()].rstrip().endswith("(")
		if not attached and AN_OWN_UNIT.match(said):
			unread.append(found.group(0) + said)
			continue
		fragments.append((usd, said, attached))

	unread.append(paid[at:])
	left = " ".join(part.strip(" .") for part in unread if part.strip(" ."))
	return _rates_for(fragments, kind, modality, per, unit), left


def _rates_for(
	fragments: list[tuple[float, str, bool]], kind: str, modality: str, per: int, unit: str
) -> list[Rate]:
	"""The fragments of one cell turned into rates, modalities resolved.

	Resolved rather than read one at a time because Google writes
	`$3.00 or $0.005/min (audio)`: two spellings of one price, with the one
	parenthetical that says what they are for sitting after the second. Reading
	each amount alone makes the first of them a text price, which it is not.
	"""
	named = [_modalities(said) for _usd, said, _attached in fragments]
	for at in range(len(named) - 1, -1, -1):
		if named[at] or not fragments[at][1].strip(" .").endswith("or"):
			continue
		named[at] = named[at + 1] if at + 1 < len(named) else []

	rates = []
	for (usd, said, attached), modalities in zip(fragments, named, strict=True):
		own, own_per = _own_unit(said) if attached else ("", 1)
		starts, ends = _when(said)
		for one in modalities or [modality]:
			rates.append(
				Rate(
					kind=kind,
					modality=one,
					unit=own or unit,
					per=own_per if own else per,
					usd=usd,
					starts=starts,
					ends=ends,
				)
			)
	return rates


#: What a parenthetical after an amount may say about what it covers. Google
#: writes `(text / image / video)` and `(text and thinking)`; thinking is
#: charged as text and is not a modality of its own.
SAYS_MODALITY = {
	"text": "text",
	"thinking": "text",
	"image": "image",
	"images": "image",
	"audio": "audio",
	"video": "video",
}


def _modalities(said: str) -> list[str]:
	"""The modalities a parenthetical names, if that is all it names.

	Searched rather than anchored, because Google puts it on either side of the
	unit: `$0.10 (text / image / video)` and `$0.005/min (audio)` are both real.
	"""
	found = re.search(r"\(([^)]*)\)", said)
	if not found:
		return []
	words = [w for w in re.split(r"[^a-zA-Z]+", found.group(1)) if w and w.lower() != "and"]
	if not words or any(w.lower() not in SAYS_MODALITY for w in words):
		return []
	named = []
	for word in words:
		one = SAYS_MODALITY[word.lower()]
		if one not in named:
			named.append(one)
	return named


#: `/min`, `per image`, `/ 1,000,000 tokens`. An amount that carries its own
#: unit is not in the table's unit, and reading it as though it were is the
#: mistake this whole module exists to avoid.
AN_OWN_UNIT = re.compile(r"^\s*\(?\s*(?:/|per\b)\s*([\d.,]*\s*[a-zA-Z][a-zA-Z0-9 ]*)", re.I)


def _own_unit(said: str) -> tuple[str, int]:
	found = AN_OWN_UNIT.match(said)
	if not found:
		return "", 1
	words = found.group(1).replace(",", "").split()
	per, words = _many(words)
	return " ".join(words).strip(" ."), per


def _when(qualifier: str) -> tuple[date | None, date | None]:
	starts = ends = None
	for found in A_WHEN.finditer(qualifier):
		when = _a_day(found.group(2))
		if when is None:
			continue
		if found.group(1).lower() in ("starting", "from"):
			starts = when
		else:
			ends = when
	return starts, ends


def _a_day(said: str) -> date | None:
	found = re.match(r"([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})", said.strip())
	if not found:
		return None
	month = found.group(1).lower()
	if month not in MONTHS:
		return None
	return date(int(found.group(3)), MONTHS.index(month) + 1, int(found.group(2)))
