"""Runs of figures for a record's charts and changes: the months before a day,
what fell in each, and how much a number moved. Pure, so every module's
charts share one arithmetic and a test reads it without a site. See
one/head.py, `one_charts`.
"""

from datetime import date


def months(until: date, count: int = 12) -> list[date]:
	"""The first day of each of the `count` months ending with `until`'s,
	oldest first."""
	year, month = until.year, until.month
	out = []
	for _ in range(count):
		out.append(date(year, month, 1))
		year, month = (year, month - 1) if month > 1 else (year - 1, 12)
	return out[::-1]


def by_month(rows, until: date, count: int = 12) -> list[float]:
	"""`rows` of (day, amount) summed into those months; a day outside them is
	left out."""
	starts = months(until, count)
	where = {(one.year, one.month): i for i, one in enumerate(starts)}
	out = [0.0] * count
	for day, amount in rows:
		if not day:
			continue
		at = where.get((day.year, day.month))
		if at is not None:
			out[at] += float(amount or 0)
	return out


def change(now, before) -> float | None:
	"""How much `now` moved from `before`, in percent; nothing when there was
	nothing before to move from."""
	now, before = float(now or 0), float(before or 0)
	if not before:
		return None
	return round(100 * (now - before) / abs(before), 1)


def same_day_last_year(day: date) -> date:
	"""The day a year before, the 28th for the 29th of February."""
	try:
		return day.replace(year=day.year - 1)
	except ValueError:
		return day.replace(year=day.year - 1, day=28)


def weeks(until: date, count: int = 12) -> list[date]:
	"""The Monday of each of the `count` weeks ending with `until`'s, oldest
	first."""
	from datetime import timedelta

	monday = until - timedelta(days=until.weekday())
	return [monday - timedelta(weeks=count - 1 - i) for i in range(count)]


def by_week(rows, until: date, count: int = 12) -> list[float]:
	"""`rows` of (day, amount) summed into those weeks; a day outside them is
	left out."""
	starts = weeks(until, count)
	out = [0.0] * count
	for day, amount in rows:
		if not day:
			continue
		at = (day - starts[0]).days // 7
		if 0 <= at < count:
			out[at] += float(amount or 0)
	return out
