"""The answers a workspace is set up from (one/setup_job.py): their shape,
what is refused, and what each turns into for frappe's wizard. Pure, so
OneAdmin, the demo and the tests read it without a site. The shape is in
one/AGENTS.md, The setup job."""

from datetime import date, timedelta
from zoneinfo import available_timezones

from onedesk.one import registry
from onedesk.one.registry import fields

FIELDS = fields.IDS
"""A company's field (one/registry/fields.py)."""

CHARTS = ("Standard", "Standard with Numbers")
"""The two charts that carry both payroll accounts (docs/ACCOUNTS.md)."""

THEMES = ("Automatic", "Light", "Dark")

WEEK = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")

TOP = ("owner", "language", "time_zone", "field", "theme", "companies", "working_day", "apps", "steps", "people")
NEEDED = ("owner", "language", "time_zone", "companies")
OWNER = ("email", "first_name", "last_name", "password", "invite")
COMPANY = ("name", "country", "currency", "abbr", "chart", "year_starts")
DAY = ("starts", "ends", "days_off")
PERSON = ("email", "first_name", "last_name", "levels", "admin")


class Invalid(ValueError):
	"""Answers that can't be set up from; the message names every problem,
	and `wrong` holds them one by one, each starting with where it is."""

	def __init__(self, message: str, wrong: list[str] | None = None):
		super().__init__(message)
		self.wrong = wrong or [message]


def check(answers: dict, partial: bool = False) -> dict:
	"""The answers, or Invalid naming each unknown key and each missing or
	wrong answer; `partial`, as the wizard keeps them while it asks, leaves
	out what is not answered yet. Pure."""
	wrong: list[str] = []
	if not isinstance(answers, dict):
		raise Invalid("the answers must be a dict")
	_keys(answers, TOP, "the answers", wrong)
	wrong += [f"{key} is missing" for key in NEEDED if not answers.get(key) and not partial]
	owner = answers.get("owner") or {}
	if _is(owner, dict, "owner", wrong):
		_keys(owner, OWNER, "owner", wrong)
		_email(owner.get("email"), "owner.email", wrong)
		if not owner.get("first_name"):
			wrong.append("owner.first_name is missing")
	zone = answers.get("time_zone")
	if zone and zone not in available_timezones():
		wrong.append(f"time_zone {zone!r} is not a time zone")
	if answers.get("field") and answers["field"] not in FIELDS:
		wrong.append(f"field {answers['field']!r} is not one of {FIELDS}")
	if answers.get("theme") and answers["theme"] not in THEMES:
		wrong.append(f"theme {answers['theme']!r} is not one of {THEMES}")
	_companies(answers.get("companies"), wrong)
	_day(answers.get("working_day"), wrong)
	_apps(answers.get("apps"), wrong)
	_steps(answers.get("steps"), wrong)
	_people(answers.get("people"), wrong)
	if wrong:
		raise Invalid("; ".join(wrong), wrong)
	return answers


def _is(value, kind, where: str, wrong: list) -> bool:
	if value is None or isinstance(value, kind):
		return value is not None
	wrong.append(f"{where} must be a {kind.__name__}")
	return False


def _keys(said: dict, known: tuple, where: str, wrong: list) -> None:
	wrong += [f"{where} has an unknown key {key!r}" for key in said if key not in known]


def _email(said, where: str, wrong: list) -> None:
	if not said:
		wrong.append(f"{where} is missing")
	elif not isinstance(said, str) or "@" not in said.strip("@") or " " in said.strip():
		wrong.append(f"{where} {said!r} is not an email address")


def _companies(said, wrong: list) -> None:
	if not _is(said, list, "companies", wrong):
		return
	names = set()
	for at, one in enumerate(said):
		where = f"companies[{at}]"
		if not _is(one, dict, where, wrong):
			continue
		_keys(one, COMPANY, where, wrong)
		wrong += [f"{where}.{key} is missing" for key in ("name", "country") if not one.get(key)]
		if one.get("name") in names:
			wrong.append(f"{where}.name {one['name']!r} is given twice")
		names.add(one.get("name"))
		if one.get("chart") and one["chart"] not in CHARTS:
			wrong.append(f"{where}.chart {one['chart']!r} is not one of {CHARTS}: a country's own chart leaves payroll without its accounts (docs/ACCOUNTS.md)")
		if one.get("year_starts"):
			try:
				_month_day(one["year_starts"])
			except ValueError:
				wrong.append(f"{where}.year_starts {one['year_starts']!r} is not a day of the year as MM-DD")


def _day(said, wrong: list) -> None:
	if not _is(said, dict, "working_day", wrong):
		return
	_keys(said, DAY, "working_day", wrong)
	for key in ("starts", "ends"):
		if not _time(said.get(key)):
			wrong.append(f"working_day.{key} {said.get(key)!r} is not a time as HH:MM")
	off = said.get("days_off") or []
	if not isinstance(off, list) or any(one not in WEEK for one in off):
		wrong.append(f"working_day.days_off must be a list of {WEEK}")


def _time(said) -> bool:
	try:
		hours, minutes = str(said).split(":")[:2]
		return 0 <= int(hours) < 24 and 0 <= int(minutes) < 60
	except ValueError:
		return False


def _apps(said, wrong: list) -> None:
	if not _is(said, dict, "apps", wrong):
		return
	switches = {one.id: one for one in registry.apps() if one.kind == "app" and one.sidebar}
	for id, on in said.items():
		if id not in switches:
			wrong.append(f"apps has {id!r}, which is not an app that can be turned on or off")
		elif not isinstance(on, bool):
			wrong.append(f"apps.{id} must be true or false")
		elif not on and switches[id].kept and switches[id].kept.always():
			wrong.append(f"apps.{id} is kept and can't be turned off")


def _steps(said, wrong: list) -> None:
	if not _is(said, dict, "steps", wrong):
		return
	ids = {one.id for one in registry.apps()}
	for id, given in said.items():
		if id not in ids:
			wrong.append(f"steps has {id!r}, which has no manifest")
		elif not isinstance(given, dict) or not all(isinstance(values, dict) for values in given.values()):
			wrong.append(f"steps.{id} must be each step's key with its values")


def _people(said, wrong: list) -> None:
	if not _is(said, list, "people", wrong):
		return
	ids = {one.id for one in (*registry.apps(), *registry.parts())}
	for at, one in enumerate(said):
		where = f"people[{at}]"
		if not _is(one, dict, where, wrong):
			continue
		_keys(one, PERSON, where, wrong)
		_email(one.get("email"), f"{where}.email", wrong)
		if not one.get("first_name"):
			wrong.append(f"{where}.first_name is missing")
		levels = one.get("levels") or {}
		if not isinstance(levels, dict):
			wrong.append(f"{where}.levels must be each app's level")
			continue
		wrong += [f"{where}.levels has {id!r}, which has no manifest" for id in levels if id not in ids]
		wrong += [f"{where}.levels.{id} must be a level's name" for id, level in levels.items() if not isinstance(level, str)]


def _month_day(said: str) -> tuple[int, int]:
	month, day = (int(one) for one in said.split("-"))
	date(2001, month, day)
	return month, day


def fiscal_year(starts: str | None, today: date) -> tuple[date, date]:
	"""The financial year today is in, for a year that starts on `starts`
	(MM-DD, the first of January when not said), as erpnext's wizard picks
	it. Pure."""
	month, day = _month_day(starts or "01-01")
	start = date(today.year, month, day)
	if start > today:
		start = date(today.year - 1, month, day)
	return start, date(start.year + 1, month, day) - timedelta(days=1)


def abbreviation(name: str, taken: set | frozenset = frozenset()) -> str:
	"""A company's short name as erpnext makes one, each word's first
	letter, with a number after it when another company has it. Pure."""
	stem = "".join(word[0] for word in name.split() if word[0].isalnum()).upper() or name[:3].upper()
	found, more = stem, 1
	while found in taken:
		more += 1
		found = f"{stem}{more}"
	return found


def number_format(said: str | None) -> str:
	"""A country's number format as System Settings keeps it for figures,
	with decimals, as frappe's wizard turns it. Pure."""
	said = said or "#,###.##"
	return {"#.###": "#.###,##", "#,###": "#,###.##"}.get(said, said)


def wizard(answers: dict, currency: str, language: str, today: date) -> dict:
	"""What frappe's setup_complete is given: the first company, the region
	and the working day, never a user (the owner is One's, made after) nor a
	chart unless the numbered Standard was asked for. Pure."""
	first = answers["companies"][0]
	start, end = fiscal_year(first.get("year_starts"), today)
	said = {
		"language": language,
		"lang": language,
		"country": first["country"],
		"timezone": answers["time_zone"],
		"currency": currency,
		"company_name": first["name"],
		"company_abbr": first.get("abbr") or abbreviation(first["name"]),
		"fy_start_date": start.isoformat(),
		"fy_end_date": end.isoformat(),
		"setup_demo": 0,
		"enable_telemetry": 0,
	}
	if first.get("chart") and first["chart"] != CHARTS[0]:
		said["chart_of_accounts"] = first["chart"]
	day = answers.get("working_day")
	if day:
		said.update(onedesk_day_starts=_seconds(day["starts"]), onedesk_day_ends=_seconds(day["ends"]), onedesk_weekly_off=list(day.get("days_off") or []))
	return said


def _seconds(said: str) -> str:
	hours, minutes = str(said).split(":")[:2]
	return f"{int(hours):02d}:{int(minutes):02d}:00"


def switched(answers: dict, hidden: list[str]) -> list[str] | None:
	"""The rail rows (Sidebar names) off once the apps answer is taken: the
	ones it turns off added to those off already, the ones it turns on
	taken away. None when it says nothing. Pure."""
	said = answers.get("apps") or {}
	if not said:
		return None
	rows = {one.id: one.sidebar for one in registry.apps() if one.sidebar}
	off = set(hidden) | {rows[id] for id, on in said.items() if not on}
	return sorted(off - {rows[id] for id, on in said.items() if on})


def levels(said: dict) -> dict[str, str]:
	"""A person's levels by app name, as People keeps them, from the
	answers' levels by folder. Pure."""
	return {registry.name(id): level for id, level in (said or {}).items()}
