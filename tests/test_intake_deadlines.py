"""Intake, stage 10: deadlines counted the way the law counts them."""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from onedesk.one_intake import deadlines


def test_a_period_is_read_as_written_in_german_or_english():
	assert deadlines.period("Einspruch innerhalb eines Monats nach Bekanntgabe") == (1, "months")
	assert deadlines.period("within one month of receipt") == (1, "months")
	assert deadlines.period("innerhalb von 14 Tagen") == (14, "days")
	assert deadlines.period("binnen zwei Wochen") == (2, "weeks")
	assert deadlines.period("please pay soon") is None


def test_a_month_ends_on_the_same_day_or_the_months_last():
	assert deadlines.add(date(2026, 1, 31), 1, "months") == date(2026, 2, 28)
	assert deadlines.add(date(2026, 3, 15), 1, "months") == date(2026, 4, 15)
	assert deadlines.add(date(2026, 12, 20), 2, "months") == date(2027, 2, 20)
	assert deadlines.add(date(2026, 9, 1), 14, "days") == date(2026, 9, 15)


def test_an_authoritys_letter_counts_from_four_days_after_posting():
	said = deadlines.count("Einspruch innerhalb eines Monats", date(2026, 9, 3), "Tax Assessment", "DE", set())
	assert said["counted_from"] == date(2026, 9, 7)
	assert said["date"] == date(2026, 10, 7)
	assert said["posted"] and (said["number"], said["unit"]) == (1, "months")
	other = deadlines.count("within one month", date(2026, 9, 3), "Letter", "DE", set(), arrived=date(2026, 9, 5))
	assert other["counted_from"] == date(2026, 9, 5) and other["date"] == date(2026, 10, 5) and not other["posted"]


def test_a_weekend_or_holiday_moves_it_to_the_next_working_day():
	said = deadlines.count("within one month", date(2026, 9, 3), "Tax Assessment", "DE", {date(2026, 10, 7)})
	assert said["date"] == date(2026, 10, 8) and said["moved"]
	assert deadlines.working(date(2026, 10, 3), set()) == (date(2026, 10, 5), True), "a Saturday is Monday"


def test_notice_is_counted_back_from_the_end():
	assert deadlines.before(date(2026, 12, 31), 3, "months") == date(2026, 9, 30)
	assert deadlines.before(date(2027, 3, 31), 1, "months") == date(2027, 2, 28)
	assert deadlines.before(date(2026, 12, 31), 4, "weeks") == date(2026, 12, 3)
