"""Deadlines counted the way the law counts them (docs/INTAKE.md §6). Pure.

A letter rarely gives a date. It says "within one month of receipt", and the
day that means depends on when it counts as received and on how a month is
counted:

- **received**: a German authority's posted letter counts as received on the
  fourth day after it was posted (§ 122 AO and § 41 VwVfG, since 2025), not
  the day it was scanned; anything else from the day it arrived;
- **a month or a week** ends on the day of the later month or week with the
  same number as the day it started from, or the month's last day when there
  is none (§ 188 BGB): 31 January plus one month is 28 February;
- **a weekend or a public holiday** moves the end to the next working day
  (§ 193 BGB), by the workspace's own Holiday List.

The day it was counted from and the rule used are kept beside the date, so a
person can check the arithmetic. The model never counts; it only copies the
period as written.
"""

import calendar
import re
from datetime import date, timedelta

#: Days a German authority's posted letter takes to count as received.
POSTED_DAYS = 4

KINDS_AUTHORITY = ("Letter From an Authority", "Tax Assessment")

NUMBERS = {
	"one": 1, "a": 1, "an": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
	"ten": 10, "eleven": 11, "twelve": 12, "fourteen": 14, "thirty": 30,
	"ein": 1, "eine": 1, "einem": 1, "einer": 1, "eines": 1, "zwei": 2, "drei": 3, "vier": 4, "fünf": 5, "sechs": 6,
	"sieben": 7, "acht": 8, "neun": 9, "zehn": 10, "elf": 11, "zwölf": 12, "vierzehn": 14, "dreißig": 30,
}  # fmt: skip

UNITS = {
	"day": "days", "days": "days", "tag": "days", "tage": "days", "tagen": "days", "tages": "days",
	"week": "weeks", "weeks": "weeks", "woche": "weeks", "wochen": "weeks",
	"month": "months", "months": "months", "monat": "months", "monate": "months", "monaten": "months", "monats": "months",
	"year": "years", "years": "years", "jahr": "years", "jahre": "years", "jahren": "years", "jahres": "years",
}  # fmt: skip

WORD = re.compile(r"\d{1,3}|[a-zäöüß]+")

#: Words that may stand between a number and its unit: "two full weeks".
BETWEEN = ("weiteren", "full", "whole", "vollen")


def period(text: str | None) -> tuple[int, str] | None:
	"""The period a sentence names: "within one month" is (1, "months"),
	"innerhalb von 14 Tagen" is (14, "days"). None when it names none."""
	words = WORD.findall((text or "").lower())
	for index, count in enumerate(words):
		number = int(count) if count.isdigit() else NUMBERS.get(count)
		if not number:
			continue
		following = words[index + 1 : index + 3]
		if following and following[0] in BETWEEN:
			following = following[1:]
		unit = UNITS.get(following[0]) if following else None
		if unit:
			return number, unit
	return None


def received(posted: date, kind: str | None, country: str | None, arrived: date | None = None) -> tuple[date, bool]:
	"""The day a letter counts as received, and whether that is by the posted
	rule rather than the day it arrived."""
	if kind in KINDS_AUTHORITY and (country or "").upper() in ("DE", "GERMANY"):
		return posted + timedelta(days=POSTED_DAYS), True
	return (arrived or posted), False


def add(start: date, number: int, unit: str) -> date:
	"""The end of a period that starts on `start` (§ 188 BGB)."""
	if unit == "days":
		return start + timedelta(days=number)
	if unit == "weeks":
		return start + timedelta(weeks=number)
	months = number * (12 if unit == "years" else 1)
	year, month = divmod(start.month - 1 + months, 12)
	year, month = start.year + year, month + 1
	return date(year, month, min(start.day, calendar.monthrange(year, month)[1]))


def before(end: date, number: int, unit: str) -> date:
	"""The last day something must be done by, `number` units before `end`:
	a contract ending 31 December with three months' notice is cancelled by
	30 September."""
	if unit in ("days", "weeks"):
		return end - timedelta(days=number * (7 if unit == "weeks" else 1))
	months = number * (12 if unit == "years" else 1)
	year, month = divmod(end.month - 1 - months, 12)
	year, month = end.year + year, month + 1
	return date(year, month, min(end.day, calendar.monthrange(year, month)[1]))


def working(day: date, holidays: set) -> tuple[date, bool]:
	"""The day itself, or the next working day when it falls on a weekend or
	a holiday (§ 193 BGB), and whether it moved."""
	moved = False
	while day.weekday() >= 5 or day in holidays:
		day, moved = day + timedelta(days=1), True
	return day, moved


def count(about: str | None, posted: date | None, kind: str | None, country: str | None, holidays: set, arrived: date | None = None) -> dict | None:
	"""A deadline written as a period, counted: the date, the day it was
	counted from, and what the rule is made of, which the caller says in
	words a person can check."""
	found = period(about)
	start = posted or arrived
	if not found or not start:
		return None
	number, unit = found
	origin, posted_rule = received(start, kind, country, arrived)
	end = add(origin, number, unit)
	end, moved = working(end, holidays)
	return {"date": end, "counted_from": origin, "number": number, "unit": unit, "posted": posted_rule, "moved": moved}
