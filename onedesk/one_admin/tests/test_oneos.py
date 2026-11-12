"""What a OneOS session costs, is charged and does each minute
(one_admin/oneos.py)."""

import hashlib
import hmac
from datetime import datetime, timedelta

from onedesk.one_admin import oneos, price_list

START = datetime(2026, 11, 12, 9, 0, 0)


def _at(minutes: float = 0, seconds: float = 0) -> datetime:
	return START + timedelta(minutes=minutes, seconds=seconds)


def test_a_minute_of_standard_1_is_its_cpu_memory_disk_and_the_screen():
	per_second = 0.5 * oneos.CPU + 4 * oneos.MEMORY + 8 * oneos.DISK
	assert round(oneos.cost_a_minute("standard-1"), 8) == round(60 * per_second + oneos.STREAM_GB_AN_HOUR * oneos.EGRESS_GB / 60, 8)
	assert 0.1 < 60 * oneos.cost_a_minute("standard-1") < 0.15, "about 11 cents an hour"


def test_a_bigger_instance_costs_more_a_minute():
	minutes = [oneos.cost_a_minute(size) for size in oneos.SIZES]
	assert minutes == sorted(minutes) and len(set(minutes)) == len(minutes)


def test_a_minute_is_charged_at_the_markup_in_credits_unrounded():
	assert oneos.credits_a_minute("standard-1", 2, 100) == round(oneos.cost_a_minute("standard-1") * 200, 6)
	assert oneos.credits_a_minute("standard-1", 0, 100) == round(oneos.cost_a_minute("standard-1") * 100, 6), "no markup is cost"
	assert 0 < oneos.credits_a_minute("standard-1", price_list.MARKUP["oneos"], price_list.credits_per_dollar()) < 1


def test_the_hold_is_thirty_minutes():
	assert oneos.hold_for("standard-1", 2, 100) == round(oneos.credits_a_minute("standard-1", 2, 100) * 30, 6)


def test_the_price_list_lists_every_size_by_the_minute_and_hour():
	rows = oneos.rates(2, 100)
	assert [one["size"] for one in rows] == list(oneos.SIZES)
	assert all(abs(one["credits_an_hour"] - one["credits_a_minute"] * 60) < 0.01 for one in rows)


def test_minutes_owed_are_whole_while_running_and_the_begun_one_at_the_end():
	assert oneos.owed(START, _at(2, 59), 0) == 2
	assert oneos.owed(START, _at(2, 59), 2) == 0
	assert oneos.owed(START, _at(2, 1), 2, whole=True) == 1
	assert oneos.owed(START, _at(0, 0), 0, whole=True) == 0
	assert oneos.owed(START, _at(-1), 0) == 0
	assert oneos.owed(START, _at(1), 5) == 0, "never a refund"


def _read(state="running", idle=0):
	return {"state": state, "idle_seconds": idle, "saved_at": None}


def test_a_running_session_is_charged_each_minute():
	did = oneos.step(oneos.STARTING, START, START, 0, 0, _read(), _at(3, 10))
	assert (did.state, did.minutes, did.stop, did.renew, did.warn) == (oneos.RUNNING, 3, None, False, False)


def test_a_starting_session_is_charged_from_the_start_too():
	did = oneos.step(oneos.STARTING, START, START, 0, 0, _read("starting"), _at(2))
	assert (did.state, did.minutes, did.stop) == (oneos.STARTING, 2, None)


def test_the_hold_is_renewed_every_fifteen_minutes():
	assert not oneos.step(oneos.RUNNING, START, START, 14, 0, _read(), _at(14, 59)).renew
	assert oneos.step(oneos.RUNNING, START, START, 14, 0, _read(), _at(15)).renew
	assert not oneos.step(oneos.RUNNING, START, _at(15), 15, 0, _read(), _at(16)).renew


def test_ten_idle_minutes_warn_and_fifteen_stop():
	assert not oneos.step(oneos.RUNNING, START, START, 0, 0, _read(idle=599), _at(20)).warn
	warned = oneos.step(oneos.RUNNING, START, START, 0, 0, _read(idle=600), _at(20))
	assert warned.warn and warned.stop is None
	stopped = oneos.step(oneos.RUNNING, START, START, 19, 0, _read(idle=900), _at(20, 30))
	assert (stopped.state, stopped.stop, stopped.minutes) == (oneos.STOPPED, oneos.IDLE, 2)


def test_eight_hours_is_the_longest():
	assert oneos.step(oneos.RUNNING, START, START, 0, 0, _read(), _at(8 * 60 - 1)).stop is None
	did = oneos.step(oneos.RUNNING, START, START, 479, 0, _read(), _at(8 * 60))
	assert (did.state, did.stop, did.minutes) == (oneos.STOPPED, oneos.TIME_LIMIT, 1)


def test_two_failed_reads_in_a_row_stop_it_charged_to_the_last_answer():
	once = oneos.step(oneos.RUNNING, START, START, 5, 0, None, _at(6), last_seen=_at(5, 30))
	assert (once.state, once.stop, once.misses, once.minutes) == (oneos.RUNNING, None, 1, 0)
	twice = oneos.step(oneos.RUNNING, START, START, 5, once.misses, None, _at(7), last_seen=_at(5, 30))
	assert (twice.state, twice.stop, twice.minutes) == (oneos.STOPPED, oneos.NOT_ANSWERING, 1)


def test_an_answer_clears_the_misses():
	assert oneos.step(oneos.RUNNING, START, START, 0, 1, _read(), _at(1)).misses == 0


def test_a_container_that_stopped_by_itself_ends_the_session():
	did = oneos.step(oneos.RUNNING, START, START, 3, 0, _read("stopped"), _at(3, 20))
	assert (did.state, did.stop, did.minutes) == (oneos.STOPPED, oneos.ENDED, 1)


def test_the_browser_token_is_the_workers():
	signed = hmac.new(b"secret", b"abc12345.1700000000", hashlib.sha256).hexdigest()
	assert oneos.token("secret", "abc12345", 1700000000) == f"1700000000.{signed}"


def test_oneos_is_not_offered_during_a_trial():
	assert oneos.on_trial("Live", 14, "2026-11-01", "2026-11-12")
	assert oneos.on_trial("Live", 14, "2026-11-01", "2026-11-15")
	assert not oneos.on_trial("Live", 14, "2026-11-01", "2026-11-16")
	assert not oneos.on_trial("Live", 0, "2026-11-01", "2026-11-02")
	assert not oneos.on_trial("Overdue", 14, "2026-11-01", "2026-11-02")
