"""The weather for a workspace's places (Weather Place), for screens in
OneDisplay and beside the clock. It comes through the account
(one_admin/weather.py), which fetches it from OpenWeather once for every
workspace nearby and charges five credits a day for each place past the
first. A place only ever sends its coordinates, and the name searched for
to find it, and only while the Weather service is on (legal.py)."""

from datetime import datetime, timezone
from typing import Annotated

import frappe
from frappe import _, _lt
from frappe.utils import cint, flt

from onedesk.one import account
from onedesk.one_legal import services

SERVICE = "weather"
READING = "onedesk.one_admin.proxy.weather_reading"
PLACES = "onedesk.one_admin.proxy.weather_places"
DOCTYPE = "Weather Place"
# how long a workspace keeps the account's answer before asking again; the
# account keeps it longer, so this only spares the round trip
KEPT = 15 * 60
HELD = "one_weather:{}"
HOURS = 13

# What OpenWeather's condition codes mean, by their hundreds and then
# exactly, and the icon a screen draws for each.
CONDITIONS = (
	((800,), _lt("Clear"), "sun"),
	((801, 802), _lt("Partly Cloudy"), "cloud-sun"),
	((803, 804), _lt("Cloudy"), "cloud"),
	((7,), _lt("Fog"), "cloud-fog"),
	((3,), _lt("Drizzle"), "cloud-drizzle"),
	((5,), _lt("Rain"), "cloud-rain"),
	((6,), _lt("Snow"), "cloud-snow"),
	((2,), _lt("Thunderstorm"), "cloud-lightning"),
)


def condition(code) -> tuple[str, str]:
	"""A condition's words and icon, from its code or its hundreds. Pure."""
	code = cint(code)
	for codes, label, icon in CONDITIONS:
		if code in codes or code // 100 in codes:
			return str(label), icon
	return "", "cloud"


def forget(place: str) -> None:
	frappe.cache.delete_value(HELD.format(place))


def answer(place: str) -> dict | None:
	"""The account's answer for a place, or None while the service is off.
	The last good answer stands when the account can't be reached."""
	held = frappe.cache.get_value(HELD.format(place))
	if held and held.get("asked", 0) > _now() - KEPT:
		return held
	where = frappe.db.get_value(DOCTYPE, place, ["latitude", "longitude"], as_dict=True)
	if not where:
		return None
	try:
		said = services.call(SERVICE, account.ask, READING, latitude=flt(where.latitude), longitude=flt(where.longitude))
	except Exception:
		frappe.log_error(title=f"Weather for {place}")
		return held
	if said is None:
		return None
	said["asked"] = _now()
	frappe.cache.set_value(HELD.format(place), said)
	return said


def _now() -> float:
	return datetime.now(timezone.utc).timestamp()


def shaped(said: dict, units: str = "Metric", lang: str = "en", now: float | None = None) -> dict:
	"""The account's answer as a widget draws it: now, the next hours and the
	days, each day named in the reader's language and its numbers bare too,
	for a range drawn to scale. "Now" is the hour that covers the present.
	Pure but for the language."""
	from onedesk.one_display.programme import _babel

	now = _now() if now is None else now
	offset = cint(said.get("offset"))
	imperial = units == "Imperial"
	degree = "°F" if imperial else "°C"

	def temp(value) -> int:
		value = flt(value)
		return round(value * 9 / 5 + 32 if imperial else value)

	def local(at) -> datetime:
		return datetime.fromtimestamp(cint(at) + offset, timezone.utc)

	hours = [one for one in said.get("hours") or [] if cint(one.get("dt")) + 3600 > now][:HOURS]
	today = local(now).date()
	days = [one for one in said.get("days") or [] if local(one.get("dt")).date() >= today]
	current = hours[0] if hours else {}
	label, icon = condition(current.get("code"))
	shown_days = []
	for i, day in enumerate(days):
		day_label, day_icon = condition(day.get("code"))
		high, low = temp(day.get("high")), temp(day.get("low"))
		date = local(day.get("dt")).date().isoformat()
		if date == today.isoformat() and current:
			# the day's forecast and the hour's are two models; today holds the hour
			high, low = max(high, temp(current.get("temp"))), min(low, temp(current.get("temp")))
		shown_days.append(
			{
				"date": date,
				"label": _("Today") if i == 0 and date == today.isoformat() else _babel(date, "EEE", lang),
				"high": f"{high}{degree}",
				"low": f"{low}{degree}",
				"hi": high,
				"lo": low,
				"condition": day_label,
				"icon": day_icon,
			}
		)
	shown_hours = [
		{
			"label": _("Now") if i == 0 else local(one.get("dt")).strftime("%H:%M"),
			"temperature": f"{temp(one.get('temp'))}°",
			"icon": condition(one.get("code"))[1],
		}
		for i, one in enumerate(hours)
	]
	wind = flt(current.get("wind_speed"))
	return {
		"temperature": f"{temp(current.get('temp'))}{degree}" if current else "",
		"condition": label,
		"icon": icon,
		"wind": f"{round(wind * 2.237)} mph" if imperial else f"{round(wind * 3.6)} km/h",
		"humidity": f"{cint(current.get('humidity'))}%",
		"high": shown_days[0]["high"] if shown_days else "",
		"low": shown_days[0]["low"] if shown_days else "",
		"days": shown_days,
		"hours": shown_hours,
	}


def reading(place: str, lang: str | None = None) -> dict | None:
	"""A place's weather as a widget draws it, or None while it can't be had."""
	said = answer(place)
	if not said:
		return None
	units = frappe.db.get_value(DOCTYPE, place, "units") or "Metric"
	return shaped(said, units, lang or frappe.local.lang or "en")


def shown() -> str | None:
	"""The default place, when the bar should ask for its weather. Asks no one."""
	place = frappe.db.get_value(DOCTYPE, {"is_default": 1}, "name")
	return place if place and services.on(SERVICE) and frappe.has_permission(DOCTYPE, "read", place) else None


@frappe.whitelist()
@frappe.read_only()
def here() -> dict | None:
	"""The workspace's place and its weather now, for beside the clock."""
	place = frappe.db.get_value(DOCTYPE, {"is_default": 1}, "name")
	if not place or not services.on(SERVICE):
		return None
	frappe.has_permission(DOCTYPE, "read", place, throw=True)
	said = reading(place)
	return {"place": place, "route": ["Form", DOCTYPE, place], **said} if said else None


@frappe.whitelist()
def search(query: Annotated[str, "A town or city's name."]) -> list[dict]:
	"""Places that answer to a name, to choose one. Only the name is sent."""
	frappe.has_permission(DOCTYPE, "create", throw=True)
	said = services.call(SERVICE, account.ask, PLACES, query=query, lang=frappe.local.lang or "en")
	if said is None:
		frappe.throw(_("Turn on Weather in TrustCenter to search for a place."), title=_("Weather Is Off"))
	return said


@frappe.whitelist()
def suggest(txt: Annotated[str, "What has been typed so far."] = "") -> list[dict]:
	"""Places for the Place field's list as it is typed: each with where it
	is, so choosing one fills in the rest. Nothing while Weather is off."""
	if len((txt or "").strip()) < 2 or not services.on(SERVICE):
		return []
	return [
		{
			# The list knows a row by its value, and many towns share a name.
			"value": ", ".join(dict.fromkeys(filter(None, (one["name"], one.get("region"), one.get("country"))))),
			"label": one["name"],
			"description": ", ".join(filter(None, (one.get("region"), one.get("country")))),
			**one,
		}
		for one in search(txt) or []
	]


# What the edge worker (deploy/edge/worker.js) reads from Cloudflare for the
# request asking where it comes from: the town of its internet address,
# written with encodeURIComponent since a town's name need not be ASCII.
LOCATED = {
	"name": "X-One-City",
	"region": "X-One-Region",
	"country": "X-One-Country",
	"latitude": "X-One-Latitude",
	"longitude": "X-One-Longitude",
}


@frappe.whitelist()
@frappe.read_only()
def located() -> dict:
	"""Roughly where the person asking is, from their internet address, as
	Cloudflare places it. Nothing is asked of the browser and nothing kept."""
	from urllib.parse import unquote

	said = {key: unquote(frappe.get_request_header(header) or "").strip() for key, header in LOCATED.items()}
	if not (said["name"] and said["latitude"] and said["longitude"]):
		return {}
	return {**said, "latitude": flt(said["latitude"]), "longitude": flt(said["longitude"])}
