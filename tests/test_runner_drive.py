"""A job keeps moving while its steps finish at once (one_admin/runner.py),
each committed, stopping at a wait or a backoff, inside its time."""

from datetime import datetime
from unittest import mock

import pytest

from onedesk.one_admin import runner


@pytest.fixture
def commits():
	with mock.patch.object(runner, "frappe") as frappe:
		yield frappe.db.commit


def _drive(answers, clock=None):
	asked = iter(answers)
	with (
		mock.patch.object(runner, "_take", return_value=True),
		mock.patch.object(runner, "advance", side_effect=lambda name: next(asked)) as advance,
		mock.patch.object(runner, "monotonic", clock or (lambda: 0)),
	):
		runner._drive("JOB")
	return advance


def test_it_keeps_going_until_a_step_waits(commits):
	advance = _drive(["Pending", "Pending", "Waiting"])
	assert advance.call_count == 3 and commits.call_count == 3


def test_it_stops_when_the_job_is_finished(commits):
	assert _drive(["Pending", "Done"]).call_count == 2


def test_it_stops_when_its_time_is_up(commits):
	moments = iter([0, runner.A_JOB_SECONDS])
	advance = _drive(["Pending", "Pending"], clock=lambda: next(moments))
	assert advance.call_count == 1, "a step that overruns the budget ends the drive"


def test_a_job_another_worker_holds_is_left_alone(commits):
	with mock.patch.object(runner, "_take", return_value=False), mock.patch.object(runner, "advance") as advance:
		runner._drive("JOB")
	assert not advance.called


def test_taking_a_job_asks_for_the_row_without_waiting_for_it():
	held = mock.MagicMock(status="Pending", next_run_at="2020-01-01 00:00:00")
	with mock.patch.object(runner, "frappe") as frappe, mock.patch.object(runner, "now_datetime", return_value=datetime(2026, 11, 10)):
		frappe.db.get_value.return_value = held
		assert runner._take("JOB")
	assert frappe.db.get_value.call_args.kwargs == {"as_dict": True, "for_update": True, "skip_locked": True}


def test_a_job_backing_off_is_not_taken():
	later = mock.MagicMock(status="Waiting", next_run_at="2999-01-01 00:00:00")
	with mock.patch.object(runner, "frappe") as frappe, mock.patch.object(runner, "now_datetime", return_value=datetime(2026, 11, 10)):
		frappe.db.get_value.return_value = later
		assert not runner._take("JOB")


def test_a_paid_signup_starts_after_the_payment_is_committed():
	with (
		mock.patch.object(runner, "start", return_value="JOB-1"),
		mock.patch.object(runner.frappe, "enqueue") as enqueue,
	):
		assert runner.start_now("acme") == "JOB-1"
	assert enqueue.call_args.args == ("onedesk.one_admin.runner.run",)
	said = enqueue.call_args.kwargs
	assert said["enqueue_after_commit"] and said["deduplicate"] and said["name"] == "JOB-1"


def test_a_throw_is_counted_and_committed(commits):
	with (
		mock.patch.object(runner, "_drive", side_effect=RuntimeError("no")),
		mock.patch.object(runner, "_counted") as counted,
	):
		runner.run("JOB")
	assert counted.call_args.args[0] == "JOB" and commits.called
