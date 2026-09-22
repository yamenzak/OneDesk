"""Whether a press failure is worth trying again, read back without a site.

`onedesk/one_admin/faults.py` imports nothing of Frappe for this reason. The
decision it makes is small and its failure mode is invisible: a provisioning
queue that retries a permanent failure looks busy forever, and one that gives up
on a rate limit strands a customer who paid.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from onedesk.one_admin import faults


@pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
def test_a_rate_limit_or_a_bad_moment_is_worth_another_attempt(status):
	assert faults.worth_retrying(status)


@pytest.mark.parametrize("status", [400, 401, 403, 404, 409, 422])
def test_our_own_bad_request_will_be_bad_forever(status):
	assert not faults.worth_retrying(status)


def test_the_exception_says_which_kind_it_is():
	assert isinstance(faults.raised("press.api.site.new", 503, "busy"), faults.Again)
	assert not isinstance(faults.raised("press.api.site.new", 400, "no"), faults.Again)


def test_catching_refused_catches_both():
	"""A caller who does not care about the difference names one exception."""
	assert issubclass(faults.Again, faults.Refused)


def test_the_exception_carries_what_a_job_needs_to_record():
	raised = faults.raised("press.api.site.new", 400, "Subdomain already exists")
	assert raised.status == 400
	assert raised.detail == "Subdomain already exists"
	assert "Subdomain already exists" in str(raised)


def test_a_thrown_message_beats_a_traceback():
	body = {"exception": "Traceback (most recent call last) ...", "_server_messages": "Site exists"}
	assert faults.detail(body, "") == "Site exists"


def test_a_body_that_is_not_json_falls_back_to_the_text():
	assert faults.detail(None, "<html>502 Bad Gateway</html>") == "<html>502 Bad Gateway</html>"


def test_a_body_with_nothing_familiar_in_it_is_still_said():
	assert faults.detail({"odd": "shape"}, "") == "{'odd': 'shape'}"


def test_nothing_recorded_is_longer_than_a_field_somebody_reads():
	assert len(faults.detail({"message": "x" * 5000}, "")) == faults.KEPT
	assert len(faults.detail(None, "y" * 5000)) == faults.KEPT
