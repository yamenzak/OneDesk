from datetime import datetime, timedelta

from onedesk.one_admin import health, servers


def test_a_workspace_is_told_once_and_forgotten_when_gone():
	held, told = health.tallied({"a": 2, "gone": 5}, {"a": False, "b": True})
	assert held == {"a": 3}
	assert told == [("a", "down")]
	held, told = health.tallied({"a": 3}, {"a": True})
	assert held == {}
	assert told == [("a", "back")]


def test_a_stretch_is_long_enough_to_have_told_anybody():
	start = datetime(2026, 11, 9, 12, 0)
	rows = [{"service": "Stripe", "checked_at": start + timedelta(minutes=5 * one), "detail": "Answered 500"} for one in range(3)]
	rows.append({"service": "Stripe", "checked_at": start + timedelta(hours=2), "detail": "Answered 500"})
	found = health.stretches(rows)
	assert len(found) == 1
	assert found[0]["checks"] == 3
	assert found[0]["started"] == start


def test_backups_are_hourly_so_their_stretch_allows_it():
	start = datetime(2026, 11, 9, 12, 0)
	rows = [{"service": "Backups", "checked_at": start + timedelta(hours=one), "detail": ""} for one in range(3)]
	assert health.stretches(rows)[0]["checks"] == 3


def test_a_day_says_the_share_of_its_checks_that_failed():
	rows = [{"service": "R2", "state": "Failing", "day": "2026-11-09", "checks": 1}, {"service": "R2", "state": "Working", "day": "2026-11-09", "checks": 3}]
	assert health._days(rows)[0]["share"] == 25.0


def test_pilot_is_told_to_warn_of_a_site_down_and_up():
	body = servers.limits_body("https://a", "secret")
	assert body["resource_limits"]["site_uptime"] is True
	assert {"site_down", "site_up"} <= set(body["webhook_endpoints"][0]["events"])


def test_the_sites_a_pilot_event_names():
	assert servers.sites_of({"site": "a.test", "context": {"sites": [{"site": "a.test"}, {"site": "b.test"}]}}) == ["a.test", "b.test"]
	assert servers.sites_of({"site": "a.test", "context": {"bench": "x"}}) == ["a.test"]
	assert servers.sites_of({"context": {}}) == []


def test_sending_fails_once_bounces_and_suppressions_pass_the_line():
	assert health.reputation(0, 0, 0) == {"sent": 0, "bounced": 0, "suppressed": 0, "share": 0.0, "over": False}
	assert not health.reputation(50, 5, 5)["over"], "too few sends to judge by"
	assert health.reputation(200, 3, 2)["share"] == 2.5 and health.reputation(200, 3, 2)["over"]
	assert not health.reputation(200, 2, 2)["over"]
	assert health.SENDING in health.CHECKS
