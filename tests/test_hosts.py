"""What a workspace may call itself, read back without a site.

`onedesk/one_admin/hosts.py` imports nothing of Frappe for the same reason
`keys.py` does not: a mistake here is a workspace claiming a name that routes
somebody else's traffic, and it would not show up in a test that needed press.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from onedesk.one_admin import hosts

SERVED = ("t.4dl.app", "admin.4dl.app")


def test_an_ordinary_domain_is_kept_as_typed():
	assert hosts.tidy("hr.acme.com") == "hr.acme.com"


def test_an_apex_is_a_domain():
	assert hosts.tidy("acme.com") == "acme.com"


@pytest.mark.parametrize(
	"pasted",
	[
		"HR.Acme.Com",
		"  hr.acme.com  ",
		"https://hr.acme.com",
		"http://hr.acme.com/app/home",
		"hr.acme.com.",
		"https://hr.acme.com/?next=/app",
		"hr.acme.com/../x",
	],
)
def test_what_somebody_pastes_is_tidied_to_one_name(pasted):
	"""The box is next to a link, so somebody will paste a URL into it.

	The path is dropped rather than refused, including a silly one: what is being
	read is the host, and `hr.acme.com/../x` names the same host as `hr.acme.com`.
	"""
	assert hosts.tidy(pasted) == "hr.acme.com"


@pytest.mark.parametrize(
	"refused",
	[
		"",
		"   ",
		"localhost",
		"acme",
		"hr.acme.com:8000",
		"hr..acme.com",
		"-hr.acme.com",
		"hr-.acme.com",
		"hr.acme.c om",
		"a" * 64 + ".acme.com",
		"x." + "a" * 250 + ".com",
	],
)
def test_a_name_that_is_not_one_is_refused(refused):
	with pytest.raises(hosts.Unclaimable):
		hosts.tidy(refused)


def test_a_name_that_is_not_a_string_is_refused():
	with pytest.raises(hosts.Unclaimable):
		hosts.tidy(None)


def test_a_workspace_may_claim_its_own_name():
	assert hosts.claimable("hr.acme.com", *SERVED) == "hr.acme.com"


@pytest.mark.parametrize(
	"taken",
	["t.4dl.app", "acme.t.4dl.app", "anything.t.4dl.app", "admin.4dl.app", "T.4DL.APP"],
)
def test_a_workspace_may_not_claim_a_name_we_hand_out(taken):
	"""Nothing stops somebody typing this in, so the refusal belongs here."""
	with pytest.raises(hosts.Unclaimable):
		hosts.claimable(taken, *SERVED)


def test_a_name_that_merely_looks_like_ours_is_still_theirs():
	"""`nott.4dl.app` ends with the same letters and is not under our domain."""
	assert hosts.claimable("nott.4dl.app", *SERVED) == "nott.4dl.app"


def test_a_name_under_the_apex_is_not_ours_to_refuse():
	"""We serve `t.4dl.app`, not `4dl.app`, which is the reason for the extra level."""
	assert hosts.claimable("shop.4dl.app", *SERVED) == "shop.4dl.app"


def test_ours_ignores_an_empty_served_domain():
	assert hosts.ours("hr.acme.com", "", None) is False


def test_the_given_name_is_built_not_asked_for():
	assert hosts.under("acme", "t.4dl.app") == "acme.t.4dl.app"


def test_the_given_name_needs_both_halves():
	with pytest.raises(hosts.Unclaimable):
		hosts.under("", "t.4dl.app")
	with pytest.raises(hosts.Unclaimable):
		hosts.under("acme", "")


def test_a_reserved_label_is_reserved_only_under_our_own_domain():
	assert hosts.reserved_here("admin.t.4dl.app", *SERVED) is True
	assert hosts.reserved_here("acme.t.4dl.app", *SERVED) is False
	assert hosts.reserved_here("admin.acme.com", *SERVED) is False


def test_a_served_domain_carrying_a_port_still_matches():
	"""The admin's own host has one in development and a claimed name never can.

	Without stripping it, `onedesk.localhost` did not match
	`onedesk.localhost:8002` and the admin console's own hostname was claimable.
	"""
	assert hosts.ours("onedesk.localhost", "onedesk.localhost:8002") is True
	with pytest.raises(hosts.Unclaimable):
		hosts.claimable("onedesk.localhost", "t.4dl.app", "onedesk.localhost:8002")


def test_a_served_domain_that_is_only_a_port_matches_nothing():
	assert hosts.ours("hr.acme.com", ":8002") is False
