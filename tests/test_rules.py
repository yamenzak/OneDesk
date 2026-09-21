"""The arithmetic behind a clock-in, checked without a site.

`onedesk/one_hr/rules.py` imports nothing of Frappe on purpose, so everything
that has to be exactly right — which addresses match, how far apart two
positions are, what a run of scores adds up to — can be read back here in
milliseconds rather than against a database.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from onedesk.one_hr import rules


def test_a_bare_address_is_its_own_range():
	assert rules.on_network("203.0.113.7", "203.0.113.7")
	assert rules.on_network("203.0.113.7", "203.0.113.0/24")
	assert not rules.on_network("203.0.113.7", "198.51.100.0/24")


def test_a_typo_costs_one_line_and_not_the_office():
	lines = "not-an-address\n203.0.113.0/24\n# a comment"
	assert rules.on_network("203.0.113.7", lines)
	assert len(rules.networks(lines)) == 1


def test_an_address_we_cannot_read_matches_nothing():
	assert rules.address(None) is None
	assert rules.address("hello") is None
	assert not rules.on_network(None, "203.0.113.0/24")


def test_ipv6_works_the_same_way():
	assert rules.on_network("2001:db8::1", "2001:db8::/32")
	assert not rules.on_network("2001:db8::1", "2001:dba::/32")


def test_distance_agrees_with_hrms_to_a_micrometre():
	"""The number that decides a refusal has to be the number HRMS refuses on.

	Their formula, written out here rather than imported, because this file may
	not import anything that needs a site. If they change it this fails, which
	is the point.
	"""
	from math import asin, cos, pi, sqrt

	def theirs(lat1, long1, lat2, long2):
		r, p = 6371, pi / 180
		a = (
			0.5
			- cos((lat2 - lat1) * p) / 2
			+ cos(lat1 * p) * cos(lat2 * p) * (1 - cos((long2 - long1) * p)) / 2
		)
		return 2 * r * asin(sqrt(a)) * 1000

	pairs = [
		(51.5007, -0.1246, 48.8584, 2.2945),  # Big Ben to the Eiffel Tower
		(25.2048, 55.2708, 25.1972, 55.2744),  # across one office
		(0, 0, 0, 1),  # a degree on the equator
	]
	for pair in pairs:
		assert abs(theirs(*pair) - rules.distance(*pair)) < 0.001


def test_distance_is_infinite_when_a_coordinate_is_missing():
	assert rules.distance(None, 0, 0, 0) == float("inf")


def test_within_takes_any_zone_and_not_the_nearest():
	here = (51.5007, -0.1246)
	zones = [
		{"name": "far", "latitude": 51.60, "longitude": -0.12, "radius": 200},
		{"name": "depot", "latitude": 51.5008, "longitude": -0.1247, "radius": 100},
	]
	assert rules.within(*here, zones)["name"] == "depot"
	assert rules.within(*here, [zones[0]]) is None


def test_a_zone_with_no_radius_is_not_a_zone():
	zones = [{"name": "nothing", "latitude": 51.5007, "longitude": -0.1246, "radius": 0}]
	assert rules.within(51.5007, -0.1246, zones) is None


@pytest.mark.parametrize(
	"signals,expected",
	[
		([], 100),
		(["network-unknown"], 40),
		(["network-unknown", "network-unknown"], 40),
		(["no-passkey"], 0),
		(["place-vague", "place-refused"], 65),
	],
)
def test_confidence_subtracts_once_per_signal(signals, expected):
	assert rules.confidence(signals) == expected


def test_a_signal_we_do_not_know_costs_nothing():
	assert rules.confidence(["invented"]) == 100


def test_the_three_outcomes():
	assert rules.outcome(100) == "Allowed"
	assert rules.outcome(70) == "Flagged"
	assert rules.outcome(10) == "Refused"


def test_what_is_certain_refuses_on_its_own():
	for name in ("no-passkey", "passkey-unverified", "network-unknown", "place-outside"):
		assert rules.outcome(rules.confidence([name])) == "Refused", name


def test_what_is_a_guess_only_flags():
	for name in (
		"place-vague",
		"place-refused",
		"place-absent",
		"device-shared",
		"travel-impossible",
		"session-elsewhere",
		"same-second",
		"reset-recent",
		"passkey-elsewhere",
		"network-personal",
	):
		assert rules.outcome(rules.confidence([name])) != "Refused", name


def test_no_passkey_always_refuses():
	assert rules.outcome(rules.confidence(["no-passkey"])) == "Refused"


def test_every_signal_has_a_sentence():
	for name, (weight, says) in rules.SIGNALS.items():
		assert says and says[0].isupper(), f"{name} has no readable sentence"
		assert 0 < weight <= 100, f"{name} has a weight nobody can act on"


def test_impossible_travel():
	# London to Paris in ten minutes.
	assert rules.impossible(343_000, 600)
	# The same journey by train.
	assert not rules.impossible(343_000, 2 * 3600)
	# Across the office, immediately.
	assert not rules.impossible(0, 0)


def test_standing_leans_on_the_recent():
	old_trouble = [0, 0, 100, 100, 100]
	new_trouble = [100, 100, 100, 0, 0]
	assert rules.standing(old_trouble) > rules.standing(new_trouble)
	assert rules.standing([]) == 100
	assert rules.standing([100, 100]) == 100


def test_a_proposal_needs_both_voices_and_repetition():
	assert rules.enough(votes=6, voters=3, threshold=3)
	# One person, twenty times, from their hotspot.
	assert not rules.enough(votes=20, voters=1, threshold=3)
	# Twenty people passing once through an airport.
	assert not rules.enough(votes=2, voters=20, threshold=3)


def test_a_phone_is_recognised_and_a_desktop_is_not():
	iphone = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"
	android = "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 Chrome/120 Mobile"
	laptop = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120"
	windows = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120"

	assert rules.is_phone(iphone)
	assert rules.is_phone(android)
	assert not rules.is_phone(laptop)
	assert not rules.is_phone(windows)
	assert not rules.is_phone("")


def test_an_ipad_needs_the_touch_count_because_it_claims_to_be_a_mac():
	ipad = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/17.0 Safari"
	assert not rules.is_phone(ipad, touch=0)
	assert rules.is_phone(ipad, touch=5)


def test_a_device_is_called_something_a_person_recognises():
	assert rules.device_label({"model": "Pixel 8", "platform": "Android"}) == "Pixel 8"
	assert rules.device_label({"platform": "iPhone"}) == "iPhone"
	assert rules.device_label({}) == "Phone"
	assert rules.device_label(None) == "Phone"
