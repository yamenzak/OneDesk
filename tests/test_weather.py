"""The weather (one/weather.py, one_admin/weather.py): one reading per place
about ten kilometres across, fetched again only when it is old, the first
place a day free, and the account's answer drawn as a widget draws it."""

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree  # noqa: E402

ADMIN = (tree.APP / "one_admin" / "weather.py").read_text()
WORKSPACE = (tree.APP / "one" / "weather.py").read_text()


class Refused(Exception):
	pass


def _flt(value):
	return float(value or 0)


def _cint(value):
	return int(float(value or 0))


def _lifted(source: str, names: tuple, **extra) -> dict:
	import ast

	space = {"flt": _flt, "cint": _cint, "Refused": Refused, "_": str, "_lt": str, **extra}
	for node in ast.parse(source).body:
		named = getattr(node.targets[0], "id", "") if isinstance(node, ast.Assign) else getattr(node, "name", "")
		if named in names:
			exec(ast.unparse(node), space)
	return space


def test_places_near_each_other_share_a_reading():
	cell = _lifted(ADMIN, ("cell",))["cell"]
	assert cell(52.5200, 13.4050) == cell(52.4801, 13.3720) == "52.5,13.4", "two places in one city share"
	assert cell(25.2048, 55.2708) != cell(52.52, 13.40)
	try:
		cell(91, 0)
	except Refused:
		pass
	else:
		raise AssertionError("a latitude past 90 is refused")


def test_hours_are_fetched_again_after_two_hours_and_days_after_twelve():
	space = _lifted(ADMIN, ("HOURS_KEPT", "DAYS_KEPT", "stale"))
	stale, now = space["stale"], 100_000.0
	held = {"hours": [1], "hours_at": now - 3600, "days": [1], "days_at": now - 3600}
	assert not stale(held, "hours", now) and not stale(held, "days", now)
	assert stale({**held, "hours_at": now - 2 * 3600}, "hours", now)
	assert not stale({**held, "days_at": now - 11 * 3600}, "days", now)
	assert stale({**held, "days_at": now - 12 * 3600}, "days", now)
	assert stale({}, "hours", now), "nothing held is fetched"


def test_a_place_a_day_is_free_and_each_other_is_charged_once():
	space = _lifted(ADMIN, ("FREE_PLACES", "charged"))
	charged = space["charged"]
	assert not charged(set(), "25.2,55.3"), "the first place today is free"
	assert not charged({"25.2,55.3"}, "25.2,55.3"), "a place served today is not charged again"
	assert charged({"25.2,55.3"}, "52.5,13.4"), "the second place is charged"


def test_only_what_a_screen_draws_is_kept_and_nothing_with_the_key():
	space = _lifted(ADMIN, ("HOUR", "DAY", "kept"))
	hour = space["kept"](
		{"dt": 1, "temp": 8.6, "humidity": 87, "wind_speed": 2.1, "pop": 0, "pressure": 1031, "weather": [{"id": 804, "icon": "04n"}]},
		space["HOUR"],
	)
	assert hour == {"dt": 1, "temp": 8.6, "humidity": 87, "wind_speed": 2.1, "pop": 0, "code": 804, "night": True}
	day = space["kept"]({"dt": 2, "temp": {"min": 6.9, "max": 13.3}, "weather": [{"id": 802, "icon": "03d"}]}, space["DAY"])
	assert (day["high"], day["low"], day["code"]) == (13.3, 6.9, 802)
	assert "appid" not in ADMIN.split("def _get")[0], "the key goes on only in _get"


def test_places_found_by_name_are_named_in_the_readers_language():
	found = _lifted(ADMIN, ("found",))["found"]
	answer = [
		{"name": "Dubai", "local_names": {"ar": "دبي"}, "lat": 25.2647227, "lon": 55.2924146, "country": "AE", "state": "Dubai"},
		{"name": "Nowhere"},
	]
	assert found(answer, "ar") == [{"name": "دبي", "region": "Dubai", "country": "AE", "latitude": 25.2647, "longitude": 55.2924}]
	assert found(answer, "de")[0]["name"] == "Dubai", "the name OpenWeather gives where there is none in the language"


def test_conditions_are_read_by_their_hundreds():
	condition = _lifted(WORKSPACE, ("CONDITIONS", "condition"))["condition"]
	assert condition(800) == ("Clear", "sun")
	assert condition(802)[1] == "cloud-sun" and condition(804)[1] == "cloud"
	assert condition(501)[1] == "cloud-rain" and condition(211)[1] == "cloud-lightning"
	assert condition(741)[1] == "cloud-fog" and condition(601)[1] == "cloud-snow"


def test_now_is_the_hour_that_covers_the_present():
	space = _lifted(
		WORKSPACE,
		("HOURS", "CONDITIONS", "condition", "_now", "shaped"),
		datetime=datetime,
		timezone=timezone,
	)
	import types

	sys.modules.setdefault("onedesk", types.ModuleType("onedesk"))
	sys.modules.setdefault("onedesk.one_display", types.ModuleType("onedesk.one_display"))
	programme = types.ModuleType("onedesk.one_display.programme")
	programme._babel = lambda day, pattern, lang: f"day:{day}"
	sys.modules["onedesk.one_display.programme"] = programme
	start = 1_793_433_600
	said = {
		"offset": 4 * 3600,
		"hours": [{"dt": start + i * 3600, "temp": 30 + i, "humidity": 40, "wind_speed": 5, "code": 800} for i in range(20)],
		"days": [{"dt": start - 86400 + i * 86400, "high": 33, "low": 26, "code": 800} for i in range(10)],
	}
	shown = space["shaped"](said, "Metric", "en", now=start + 2 * 3600 + 60)
	assert shown["temperature"] == "32°C", "two hours on, now is the third hour held"
	assert shown["hours"][0]["label"] == "Now" and len(shown["hours"]) == 13
	assert shown["wind"] == "18 km/h" and shown["days"][0]["label"] == "Today"
	assert shown["high"] == "33°C", "today's high is the day's forecast"
	hot = space["shaped"]({**said, "hours": [{**one, "temp": 36} for one in said["hours"]]}, "Metric", "en", now=start)
	assert hot["high"] == "36°C", "but never below the hour's own temperature"
	imperial = space["shaped"](said, "Imperial", "en", now=start)
	assert imperial["temperature"] == "86°F" and imperial["wind"] == "11 mph"
