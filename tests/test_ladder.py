"""When a workspace falls, read back without a site.

`onedesk/one_admin/ladder.py` imports nothing of Frappe because this is the
module that decides when somebody's data is deleted. Every case that could lose
data early is here, including the two that are answered by doing nothing.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from onedesk.one_admin import ladder

NOW = datetime(2026, 6, 1, 12, 0, 0)


def ago(days):
	return NOW - timedelta(days=days)


def test_the_rungs_are_in_order_and_end():
	assert ladder.RUNGS[0] == "Live"
	assert ladder.RUNGS[-1] == "Dropped"
	assert ladder.below("Dropped") is None


def test_each_rung_leads_to_the_next():
	assert ladder.below("Live") == "Overdue"
	assert ladder.below("Overdue") == "Suspended"
	assert ladder.below("Suspended") == "Archived"
	assert ladder.below("Archived") == "Dropped"


def test_a_status_that_is_not_a_rung_goes_nowhere():
	"""Requested, Provisioning and Failed are real statuses and not on the ladder."""
	for other in ("Requested", "Provisioning", "Failed", ""):
		assert ladder.below(other) is None
		assert ladder.due(other, ago(999), NOW) is None


def test_a_workspace_that_has_not_waited_long_enough_stays():
	assert ladder.due("Overdue", ago(6), NOW) is None


def test_a_workspace_falls_on_the_day_the_period_runs_out():
	assert ladder.due("Overdue", ago(7), NOW) == "Suspended"


def test_it_keeps_falling_once_it_is_late():
	assert ladder.due("Suspended", ago(14), NOW) == "Archived"
	assert ladder.due("Archived", ago(30), NOW) == "Dropped"


def test_a_workspace_with_no_timestamp_never_falls():
	"""A failed migration must not be a reason to delete somebody's files."""
	assert ladder.due("Overdue", None, NOW) is None
	assert ladder.falls("Overdue", None, NOW) == []


def test_a_period_of_zero_means_never_rather_than_immediately():
	"""Clearing the grace period asks for the ladder to stop, not for tonight."""
	assert ladder.due("Overdue", ago(999), NOW, {"Overdue": 0}) is None
	assert ladder.days_left("Overdue", ago(1), NOW, {"Overdue": 0}) is None


def test_a_negative_period_is_read_the_same_way():
	assert ladder.due("Overdue", ago(999), NOW, {"Overdue": -3}) is None


def test_a_missing_period_leaves_the_rung_alone():
	assert ladder.due("Overdue", ago(999), NOW, {}) is None


def test_live_never_falls_on_its_own():
	"""Only a payment failing moves a workspace off Live, and that is not a clock."""
	assert ladder.due("Live", ago(999), NOW) is None


def test_a_workspace_nobody_looked_at_walks_every_rung():
	walked = ladder.falls("Overdue", ago(365), NOW)
	assert walked == ["Suspended", "Archived", "Dropped"]


def test_it_walks_only_as_far_as_the_clock_allows():
	assert ladder.falls("Overdue", ago(7), NOW) == ["Suspended"]
	assert ladder.falls("Overdue", ago(14), NOW) == ["Suspended", "Archived"]


def test_a_workspace_that_is_not_late_walks_nowhere():
	assert ladder.falls("Overdue", ago(1), NOW) == []


def test_paying_goes_straight_back_to_live_from_any_rung():
	for rung in ("Overdue", "Suspended", "Archived"):
		assert ladder.climbing(rung) == "Live"


def test_a_dropped_workspace_cannot_be_restored():
	"""There is nothing left, and answering Live would be a lie a screen draws."""
	with pytest.raises(ladder.Unreachable):
		ladder.climbing("Dropped")


def test_only_the_rungs_that_owe_money_say_so():
	assert ladder.owing("Live") is False
	assert ladder.owing("Dropped") is False
	for rung in ("Overdue", "Suspended", "Archived"):
		assert ladder.owing(rung) is True


def test_the_days_left_are_what_a_customer_is_told():
	assert ladder.days_left("Overdue", ago(0), NOW) == 7
	assert ladder.days_left("Overdue", ago(6), NOW) == 1
	assert ladder.days_left("Overdue", ago(7), NOW) == 0


def test_days_left_never_goes_negative():
	assert ladder.days_left("Overdue", ago(99), NOW) == 0


def test_days_left_is_none_off_the_ladder():
	assert ladder.days_left("Dropped", ago(1), NOW) is None
	assert ladder.days_left("Overdue", None, NOW) is None
