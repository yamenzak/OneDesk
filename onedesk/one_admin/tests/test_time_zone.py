"""A new workspace keeps the signup's time zone, not frappe's Asia/Kolkata
fallback (one_admin/signup.py zone, one/account.py)."""

from onedesk.one import account
from onedesk.one_admin import signup


def test_a_signup_keeps_the_zone_its_browser_said():
	assert signup.zone("Europe/Berlin") == "Europe/Berlin"
	assert signup.zone(" America/New_York ") == "America/New_York"


def test_a_signup_that_said_none_or_nonsense_is_utc():
	assert signup.zone(None) == "UTC"
	assert signup.zone("") == "UTC"
	assert signup.zone("Mars/Olympus") == "UTC"


def test_a_workspace_before_its_wizard_says_no_zone_and_takes_admins():
	assert account.zone_to_say(False, None) is None, "frappe's fallback must not overwrite the signup's"
	assert account.zone_to_say(False, "Asia/Kolkata") is None
	assert account.zone_to_take(False, None, "Europe/Berlin") == "Europe/Berlin"


def test_a_workspace_after_its_wizard_says_its_own_and_takes_nothing():
	assert account.zone_to_say(True, "Asia/Dubai") == "Asia/Dubai"
	assert account.zone_to_say(True, None) is None
	assert account.zone_to_take(True, "Asia/Dubai", "Europe/Berlin") is None


def test_nothing_is_taken_when_they_already_agree_or_admin_has_none():
	assert account.zone_to_take(False, "Europe/Berlin", "Europe/Berlin") is None
	assert account.zone_to_take(False, None, None) is None
