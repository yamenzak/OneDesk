"""Where a widget's words come from (one_display/AGENTS.md, Sources). A
`Display Source` is read on the server, as the person who saved it, and only
the fields a widget's mapping names leave it, already formatted in the
channel's language. What was read is kept for the source's interval, so a
hundred screens on one channel cost one query."""

import hashlib
import json
import re
from contextlib import contextmanager
from typing import Annotated

import frappe
from frappe import _, _lt
from frappe.utils import cint, flt, strip_html

from onedesk.one_display import queue as queues
from onedesk.one_legal import services

DOCTYPE = "Display Source"
KEPT = {"Records": 60, "Record": 60, "Report": 300, "Queue": 0, "Feed": 900, "Weather": 1800, "Exchange Rates": 3600}
# What a row of an Exchange Rates source carries, for mapping.
RATE_FIELDS = ("currency", "rate", "base", "line")
MOST_ROWS = 50
FIELD = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
WEATHER = "display_weather"
FETCHED = 1024 * 1024


def fields_in(mapping: dict) -> set[str]:
	"""Every field a mapping names: `{field}` in a line, or a bare field name."""
	found = set()
	for line in (mapping or {}).values():
		line = str(line or "")
		named = FIELD.findall(line)
		found.update(named if named else ([line] if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", line) else []))
	return found


def _line(template: str, row: dict) -> str:
	template = str(template or "")
	if not FIELD.search(template):
		return row.get(template, "") if template in row else template
	return FIELD.sub(lambda found: str(row.get(found.group(1), "")), template).strip()


@contextmanager
def _as(user: str):
	"""Read as the person who saved the source, and back again."""
	was = frappe.session.user
	if not user or not frappe.db.get_value("User", user, "enabled"):
		frappe.throw(_("This source has nobody to read as."), frappe.PermissionError)
	frappe.set_user(user)
	try:
		yield
	finally:
		frappe.set_user(was)


def _formatted(value, df=None) -> str:
	if value is None or value == "":
		return ""
	if df is not None:
		return strip_html(str(frappe.format_value(value, df) or "")).strip()
	return str(value)


def _picture(value) -> str:
	"""A picture a screen can load without signing in: a public file or an
	address on the web, nothing private."""
	value = str(value or "")
	return value if value.startswith(("/files/", "https://", "http://")) else ""


def _key(source, fields: set[str], lang: str) -> str:
	said = json.dumps([source.name, str(source.modified), sorted(fields), lang, frappe.cache.get_value(FRESH.format(source.name))])
	return "one_display:source:" + hashlib.sha1(said.encode()).hexdigest()


# changed when a record the source reads is saved (live.record_saved), so every kept answer is passed over
FRESH = "one_display:source_fresh:{}"


def forget(name: str) -> None:
	"""The source is read again the next time it is asked."""
	frappe.cache.set_value(FRESH.format(name), frappe.generate_hash(length=8))


def read(name: str, fields: set[str] | None = None, lang: str | None = None) -> list[dict]:
	"""The source's rows, each field formatted as text. The last good answer
	stands when a read fails, so a screen keeps showing something."""
	source = frappe.get_cached_doc(DOCTYPE, name)
	fields = set(fields or ())
	lang = lang or frappe.local.lang or "en"
	key = _key(source, fields, lang)
	kept = cint(source.refresh) or KEPT.get(source.kind, 60)
	if kept:
		hit = frappe.cache.get_value(key)
		if hit is not None:
			return hit
	try:
		rows = _read(source, fields, lang)
	except Exception:
		frappe.log_error(title=f"OneDisplay source {name}")
		rows = frappe.cache.get_value(key + ":last") or []
		frappe.cache.set_value(key, rows, expires_in_sec=max(kept, 30))
		return rows
	if kept:
		frappe.cache.set_value(key, rows, expires_in_sec=kept)
	frappe.cache.set_value(key + ":last", rows)
	return rows


def _read(source, fields: set[str], lang: str) -> list[dict]:
	previous = frappe.local.lang
	frappe.local.lang = lang
	try:
		if source.kind == "Queue":
			return [queues.board(source.queue)]
		if source.kind == "Feed":
			return _feed(source.feed_url)
		if source.kind == "Exchange Rates":
			return _rates(source)
		if source.kind == "Weather":
			said = services.call(WEATHER, _weather, source.latitude, source.longitude, source.units)
			return [said] if said else []
		with _as(source.read_as or source.owner):
			if source.kind == "Records":
				return _records(source, fields)
			if source.kind == "Record":
				return _record(source, fields)
			if source.kind == "Report":
				return _report(source, fields)
	finally:
		frappe.local.lang = previous
	return []


def _allowed(doctype: str, fields: set[str]) -> list[str]:
	"""The fields asked for that the reader may see, and nothing else."""
	from frappe.model import get_permitted_fields

	permitted = set(get_permitted_fields(doctype, user=frappe.session.user)) | {"name"}
	return sorted(field for field in fields if field in permitted)


def _records(source, fields: set[str]) -> list[dict]:
	filters = json.loads(source.filters or "[]")
	if source.aggregate:
		target = source.aggregate_field if source.aggregate != "Count" else "*"
		if source.aggregate != "Count" and target not in _allowed(source.ref_doctype, {target}):
			return []
		function = {"Count": "COUNT", "Sum": "SUM", "Average": "AVG"}[source.aggregate]
		said = frappe.get_list(source.ref_doctype, filters=filters, fields=[{function: target, "as": "value"}])
		value = said[0].value if said else 0
		df = frappe.get_meta(source.ref_doctype).get_field(target) if target != "*" else None
		return [{"value": _formatted(flt(value) if source.aggregate != "Count" else cint(value), df) or "0"}]
	asked = _allowed(source.ref_doctype, fields)
	meta = frappe.get_meta(source.ref_doctype)
	rows = frappe.get_list(
		source.ref_doctype,
		filters=filters,
		fields=list({"name", *asked}),
		order_by=source.order_by or "modified desc",
		limit=min(cint(source.row_limit) or 10, MOST_ROWS),
	)
	return [{field: _shown(meta, field, row.get(field)) for field in asked} for row in rows]


def _shown(meta, field: str, value) -> str:
	df = meta.get_field(field)
	if df and df.fieldtype in ("Attach Image", "Attach"):
		return _picture(value)
	return _formatted(value, df)


def _record(source, fields: set[str]) -> list[dict]:
	doc = frappe.get_doc(source.ref_doctype, source.record_name)
	doc.check_permission("read")
	meta = frappe.get_meta(source.ref_doctype)
	return [{field: _shown(meta, field, doc.get(field)) for field in _allowed(source.ref_doctype, fields)}]


def _report(source, fields: set[str]) -> list[dict]:
	from frappe.desk.query_report import run

	frappe.has_permission("Report", "read", doc=source.report, throw=True)
	said = run(source.report, filters=json.loads(source.report_filters or "{}"), ignore_prepared_report=True)
	columns = []
	for column in said.get("columns") or []:
		if isinstance(column, str):
			label, _sep, kind = column.partition(":")
			column = {"label": label, "fieldname": frappe.scrub(label), "fieldtype": (kind.split("/")[0] or "Data")}
		columns.append(frappe._dict(column))
	named = {column.fieldname: column for column in columns}
	rows = []
	for row in (said.get("result") or [])[:MOST_ROWS]:
		if isinstance(row, (list, tuple)):
			row = {columns[i].fieldname: value for i, value in enumerate(row) if i < len(columns)}
		if not isinstance(row, dict):
			continue
		rows.append({field: _formatted(row.get(field), named.get(field)) for field in fields if field in named})
	return rows


def _public(url: str) -> str:
	"""The feed's address, if it is https and every address its host names is
	on the public internet: a feed never reaches the workspace's own network."""
	import ipaddress
	import socket
	from urllib.parse import urlparse

	parsed = urlparse(url or "")
	if parsed.scheme != "https" or not parsed.hostname:
		raise ValueError("a feed is read over https")
	for *_rest, address in socket.getaddrinfo(parsed.hostname, parsed.port or 443, proto=socket.IPPROTO_TCP):
		if not ipaddress.ip_address(address[0]).is_global:
			raise ValueError("a feed is read from the public internet")
	return url


def currencies_in(said: str | None) -> list[str]:
	"""USD, eur gbp → ["USD", "EUR", "GBP"], each once, in the order given."""
	return list(dict.fromkeys(one.strip().upper() for one in re.split(r"[,\s]+", said or "") if one.strip()))


def _rates(source) -> list[dict]:
	"""What one of each currency is worth in the base currency, by ERPNext's
	own rates: the workspace's Currency Exchange records first, then the
	provider its Accounts Settings name, so a screen shows what the books
	use."""
	from erpnext.setup.utils import get_exchange_rate

	company = frappe.db.get_default("company")
	base = source.base_currency or (frappe.get_cached_value("Company", company, "default_currency") if company else None)
	if not base:
		return []
	rows = []
	for currency in currencies_in(source.currencies):
		if currency == base:
			continue
		rate = get_exchange_rate(currency, base)
		if not rate:
			continue
		shown = frappe.format_value(flt(rate, 4), {"fieldtype": "Float", "precision": 4})
		rows.append({"currency": currency, "rate": shown, "base": base, "line": f"{currency} {shown} {base}"})
	return rows


def _feed(url: str) -> list[dict]:
	"""An RSS or Atom feed's newest items, as text: a title, a line of what
	it says, when, and a picture where the feed gives one."""
	import requests
	from defusedxml import ElementTree as ET

	answer = requests.get(_public(url), timeout=8, headers={"User-Agent": "OneDisplay"}, stream=True, allow_redirects=False)
	answer.raise_for_status()
	body = answer.raw.read(FETCHED + 1, decode_content=True)
	if len(body) > FETCHED:
		raise ValueError("feed too large")
	root = ET.fromstring(body)
	items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
	rows = []
	for item in items[:MOST_ROWS]:
		def text(*names):
			for name in names:
				found = item.find(name)
				if found is not None and (found.text or "").strip():
					return found.text.strip()
			return ""

		atom = "{http://www.w3.org/2005/Atom}"
		media = item.find("{http://search.yahoo.com/mrss/}content")
		if media is None:
			media = item.find("{http://search.yahoo.com/mrss/}thumbnail")
		enclosure = item.find("enclosure")
		image = (media.get("url") if media is not None else "") or (
			enclosure.get("url") if enclosure is not None and (enclosure.get("type") or "").startswith("image") else ""
		)
		link = text("link") or (item.find(f"{atom}link").get("href") if item.find(f"{atom}link") is not None else "")
		rows.append(
			{
				"title": strip_html(text("title", f"{atom}title")),
				"summary": strip_html(text("description", f"{atom}summary", f"{atom}content"))[:280],
				"date": text("pubDate", f"{atom}updated", f"{atom}published"),
				"link": link if link.startswith("http") else "",
				"image": image if image.startswith("https://") else "",
			}
		)
	return rows


# What WMO's weather codes mean, as Open-Meteo answers them, and the icon a
# screen draws for each.
CONDITIONS = (
	((0,), _lt("Clear"), "sun"),
	((1, 2), _lt("Partly Cloudy"), "cloud-sun"),
	((3,), _lt("Cloudy"), "cloud"),
	((45, 48), _lt("Fog"), "cloud-fog"),
	((51, 53, 55, 56, 57), _lt("Drizzle"), "cloud-drizzle"),
	((61, 63, 65, 66, 67, 80, 81, 82), _lt("Rain"), "cloud-rain"),
	((71, 73, 75, 77, 85, 86), _lt("Snow"), "cloud-snow"),
	((95, 96, 99), _lt("Thunderstorm"), "cloud-lightning"),
)


def condition(code) -> tuple[str, str]:
	code = cint(code)
	for codes, label, icon in CONDITIONS:
		if code in codes:
			return _(label), icon
	return "", "cloud"


def _weather(latitude, longitude, units: str = "Metric") -> dict:
	"""Now and the next days from Open-Meteo, which asks for no key and is
	told only the place."""
	import requests

	imperial = units == "Imperial"
	answer = requests.get(
		"https://api.open-meteo.com/v1/forecast",
		params={
			"latitude": flt(latitude),
			"longitude": flt(longitude),
			"current": "temperature_2m,weather_code,wind_speed_10m,relative_humidity_2m",
			"daily": "temperature_2m_max,temperature_2m_min,weather_code",
			"timezone": "auto",
			"forecast_days": 6,
			"temperature_unit": "fahrenheit" if imperial else "celsius",
			"wind_speed_unit": "mph" if imperial else "kmh",
		},
		timeout=8,
	)
	answer.raise_for_status()
	said = answer.json()
	now = said.get("current") or {}
	daily = said.get("daily") or {}
	label, icon = condition(now.get("weather_code"))
	degree = "°F" if imperial else "°C"
	days = []
	for i, day in enumerate(daily.get("time") or []):
		day_label, day_icon = condition((daily.get("weather_code") or [None])[i])
		days.append(
			{
				"date": day,
				"high": f"{round(flt(daily['temperature_2m_max'][i]))}{degree}",
				"low": f"{round(flt(daily['temperature_2m_min'][i]))}{degree}",
				"condition": day_label,
				"icon": day_icon,
			}
		)
	return {
		"temperature": f"{round(flt(now.get('temperature_2m')))}{degree}",
		"condition": label,
		"icon": icon,
		"wind": f"{round(flt(now.get('wind_speed_10m')))} {'mph' if imperial else 'km/h'}",
		"humidity": f"{cint(now.get('relative_humidity_2m'))}%",
		"days": days,
	}


def fill(widget, lang: str) -> dict:
	"""What one widget draws: a premade widget's whole source, or its rows
	with only the slots its mapping fills."""
	from onedesk.one_display import widgets

	if not widget.source:
		return {}
	kind = frappe.get_cached_value(DOCTYPE, widget.source, "kind")
	spec = widgets.TYPES.get(widget.widget_type) or {}
	if kind not in spec.get("sources", ()):
		return {}
	mapping = json.loads(widget.mapping or "{}")
	if not spec.get("slots"):
		rows = read(widget.source, set(), lang)
		return {"rows": rows if widget.widget_type == "Custom" and kind != "Queue" else [], "whole": rows[0] if rows else None}
	if kind in ("Feed",):
		rows = read(widget.source, set(), lang)
	else:
		rows = read(widget.source, fields_in(mapping), lang)
	slots = {slot: mapping.get(slot) for slot in spec["slots"] if mapping.get(slot)}
	if kind == "Feed" and not slots:
		slots = {"text": "{title}", "title": "{title}", "subtitle": "{summary}", "image": "{image}"}
		slots = {slot: line for slot, line in slots.items() if slot in spec["slots"]}
	filled = []
	for row in rows:
		one = {slot: _line(line, row) for slot, line in slots.items()}
		if "image" in one:
			one["image"] = _picture(one["image"])
		filled.append(one)
	return {"rows": filled}


@frappe.whitelist()
def fields_of(doctype: Annotated[str, "A record type."]) -> list[dict]:
	"""The fields a source may map, as the reader may see them."""
	frappe.has_permission(DOCTYPE, "write", throw=True)
	frappe.has_permission(doctype, "read", throw=True)
	from frappe.model import get_permitted_fields

	meta = frappe.get_meta(doctype)
	permitted = set(get_permitted_fields(doctype, user=frappe.session.user))
	return [{"fieldname": "name", "label": _("ID"), "fieldtype": "Data"}] + [
		{"fieldname": df.fieldname, "label": _(df.label), "fieldtype": df.fieldtype}
		for df in meta.fields
		if df.fieldname in permitted and df.fieldtype not in frappe.model.no_value_fields and df.fieldtype != "Table"
	]


@frappe.whitelist()
def report_fields(report: Annotated[str, "A report."], filters: Annotated[str | None, "Its filters, as JSON."] = None) -> list[dict]:
	"""A report's columns, for mapping."""
	from frappe.desk.query_report import run

	frappe.has_permission(DOCTYPE, "write", throw=True)
	frappe.has_permission("Report", "read", doc=report, throw=True)
	said = run(report, filters=json.loads(filters or "{}"), ignore_prepared_report=True)
	out = []
	for column in said.get("columns") or []:
		if isinstance(column, str):
			label = column.partition(":")[0]
			column = {"label": label, "fieldname": frappe.scrub(label)}
		out.append({"fieldname": column.get("fieldname"), "label": column.get("label") or column.get("fieldname")})
	return out


@frappe.whitelist()
def peek(
	source: Annotated[str, "The source."],
	mapping: Annotated[str | dict | None, "Slot to field, as JSON."] = None,
	widget_type: Annotated[str | None, "The widget it fills."] = None,
) -> dict:
	"""What a widget would show from a source now: the editor's preview."""
	frappe.has_permission(DOCTYPE, "read", doc=source, throw=True)
	if isinstance(mapping, str):
		mapping = json.loads(mapping or "{}")
	widget = frappe._dict(source=source, mapping=json.dumps(mapping or {}), widget_type=widget_type or "List")
	return fill(widget, frappe.local.lang)
