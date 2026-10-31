"""Weather from OpenWeather's One Call API 4.0, fetched once for every
workspace near the same place and charged to each that shows it: one place
a day free, CREDITS_A_DAY for each other. How the cells, the refresh and
the charge work is in the README, under Weather."""

from datetime import date, datetime, timezone

import frappe
import requests
from frappe.utils import cint, flt

from onedesk.one_admin import faults, ledger
from onedesk.one_admin.faults import Refused

API = "https://api.openweathermap.org/data/4.0/onecall/{part}"
GEOCODE = "https://api.openweathermap.org/geo/1.0/direct"

HOURS_KEPT = 2 * 3600
DAYS_KEPT = 12 * 3600
FREE_PLACES = 1
CREDITS_A_DAY = 5
# What one call costs us past the free thousand a day, in dollars (0.14 EUR
# for a hundred), and the calls a place makes a day: twelve for its hours,
# two for its days.
CALL_USD = 0.0014 * 1.15
CALLS_A_DAY = 24 * 3600 // HOURS_KEPT + 24 * 3600 // DAYS_KEPT
TIMEOUT = 10
MOST_PLACES = 5

HELD = "one_weather:cell:{}"
SERVED = "one_weather:served:{}:{}"
CALLS = "one_weather:calls:{}"
LOCK = "one_weather:fetching:{}"

HOUR = ("dt", "temp", "feels_like", "humidity", "wind_speed", "pop")
DAY = ("dt", "sunrise", "sunset", "humidity", "wind_speed", "pop")


def cell(latitude, longitude) -> str:
	"""The cell a place falls in, about ten kilometres across. Pure."""
	latitude, longitude = flt(latitude), flt(longitude)
	if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
		raise Refused("A latitude is between -90 and 90, and a longitude between -180 and 180.")
	return f"{round(latitude, 1):.1f},{round(longitude, 1):.1f}"


def kept(record: dict, fields: tuple) -> dict:
	"""Only what a screen draws from one record, with its condition. Pure."""
	out = {key: record[key] for key in fields if key in record}
	sky = (record.get("weather") or [{}])[0]
	out["code"] = cint(sky.get("id"))
	out["night"] = str(sky.get("icon") or "").endswith("n")
	temp = record.get("temp")
	if isinstance(temp, dict):
		out["high"], out["low"] = temp.get("max"), temp.get("min")
	return out


def stale(held: dict, part: str, now: float) -> bool:
	"""Whether a cell's hours or days are old enough to fetch again. Pure."""
	at = flt((held or {}).get(f"{part}_at"))
	return not (held or {}).get(part) or now - at >= (HOURS_KEPT if part == "hours" else DAYS_KEPT)


def charged(served: set, place: str) -> bool:
	"""Whether serving a place today costs the workspace: it is new today and
	the free places are taken. Pure."""
	return place not in served and len(served) >= FREE_PLACES


def _key() -> str:
	stored = frappe.get_cached_doc("One Admin Settings")
	key = frappe.conf.get("openweather_key") or stored.get_password("openweather_key", raise_exception=False)
	if not key:
		raise Refused("Weather is not configured. Set the OpenWeather key in OneAdmin Settings.")
	return key


def _get(url: str, params: dict) -> requests.Response:
	"""OpenWeather takes its key in the address, so a failure is raised again
	without it: nothing that names the address reaches a log or a workspace."""
	try:
		return requests.get(url, params={**params, "appid": _key()}, timeout=TIMEOUT)
	except requests.RequestException:
		raise faults.Again("OpenWeather could not be reached.") from None


def _fetch(part: str, latitude: float, longitude: float) -> dict:
	answer = _get(API.format(part=part), {"lat": latitude, "lon": longitude, "units": "metric"})
	frappe.cache.incrby(frappe.cache.make_key(CALLS.format(date.today().isoformat())), 1)
	if answer.status_code != 200:
		# the body names the parameters, never the key
		raise faults.raised(f"weather:{part}", answer.status_code, answer.text[: faults.KEPT])
	return answer.json()


def _fresh(place: str) -> dict:
	"""A cell's reading, fetching what is stale. One fetch at a time per cell,
	so workspaces asking together share it."""
	now = datetime.now(timezone.utc).timestamp()
	held = frappe.cache.get_value(HELD.format(place)) or {}
	if not (stale(held, "hours", now) or stale(held, "days", now)):
		return held
	lock = frappe.cache.make_key(LOCK.format(place))
	if not frappe.cache.set(lock, 1, nx=True, ex=30):
		return held
	try:
		latitude, longitude = (float(one) for one in place.split(","))
		if stale(held, "hours", now):
			said = _fetch("timeline/1h", latitude, longitude)
			held.update(
				hours=[kept(one, HOUR) for one in said.get("data") or []],
				hours_at=now,
				timezone=said.get("timezone"),
				offset=cint(said.get("timezone_offset")),
			)
		if stale(held, "days", now):
			said = _fetch("timeline/1day", latitude, longitude)
			held.update(days=[kept(one, DAY) for one in said.get("data") or []], days_at=now)
		frappe.cache.set_value(HELD.format(place), held)
	finally:
		frappe.cache.delete(lock)
	return held


def reading(tenant: str, latitude, longitude) -> dict:
	"""A place's next hours and days for a workspace, charged to it if it is
	past its free places today."""
	place = cell(latitude, longitude)
	served_key = SERVED.format(date.today().isoformat(), tenant)
	served = set(frappe.cache.smembers(served_key) or ())
	served = {one.decode() if isinstance(one, bytes) else one for one in served}
	holding = None
	if charged(served, place):
		holding = ledger.reserve(tenant, CREDITS_A_DAY, why="weather:place", reference=place, action="weather")
	try:
		held = _fresh(place)
	except Exception:
		if holding:
			ledger.release(holding)
		raise
	if holding:
		ledger.commit(holding, CREDITS_A_DAY, CALL_USD * CALLS_A_DAY, model="weather:openweather")
	frappe.cache.sadd(served_key, place)
	frappe.cache.expire_key(served_key, 2 * 86400)
	return {
		"place": place,
		"timezone": held.get("timezone"),
		"offset": held.get("offset") or 0,
		"hours": held.get("hours") or [],
		"days": held.get("days") or [],
		"credits": CREDITS_A_DAY if holding else 0,
	}


def places(query: str, lang: str = "en") -> list[dict]:
	"""Places that answer to a name, each with its name in the reader's
	language where OpenWeather has one. Not charged."""
	query = " ".join((query or "").split())[:100]
	if len(query) < 2:
		return []
	answer = _get(GEOCODE, {"q": query, "limit": MOST_PLACES})
	if answer.status_code != 200:
		raise faults.raised("weather:places", answer.status_code, answer.text[: faults.KEPT])
	return found(answer.json(), lang)


def found(answer: list, lang: str = "en") -> list[dict]:
	"""Geocoding's answer as places: a name, its region and country, and where
	it is. Pure."""
	out = []
	for one in answer or []:
		if "lat" not in one or "lon" not in one:
			continue
		local = (one.get("local_names") or {}).get((lang or "en").split("-")[0])
		out.append(
			{
				"name": local or one.get("name") or "",
				"region": one.get("state") or "",
				"country": one.get("country") or "",
				"latitude": round(flt(one["lat"]), 4),
				"longitude": round(flt(one["lon"]), 4),
			}
		)
	return out


def calls_today() -> int:
	"""How many calls OneAdmin has made to OpenWeather today, against the
	free thousand."""
	return cint(frappe.cache.get(frappe.cache.make_key(CALLS.format(date.today().isoformat()))))
