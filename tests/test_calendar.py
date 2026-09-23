"""OneCalendar: layers every module declares, events and who sees them, and the
link other calendar apps subscribe to.

The pure parts run here without frappe: when a repeating event happens, which
layer an event is on, how an entry is drawn, and the iCalendar file.
"""

import ast
import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

CAL = tree.APP / "one_calendar"
HOOKS = (tree.APP / "hooks.py").read_text(encoding="utf-8")


class Row(dict):
	__getattr__ = dict.get


def get_datetime(value):
	if value is None or isinstance(value, datetime):
		return value
	if isinstance(value, date):
		return datetime.combine(value, datetime.min.time())
	return datetime.fromisoformat(str(value))


def getdate(value):
	return value if isinstance(value, date) and not isinstance(value, datetime) else get_datetime(value).date()


def add_months(day, months):
	month = day.month - 1 + months
	year, month = day.year + month // 12, month % 12 + 1
	return day.replace(year=year, month=month, day=min(day.day, 28))


def _load(path: Path, names: tuple, **extra) -> dict:
	space = {
		"datetime": datetime,
		"date": date,
		"timedelta": timedelta,
		"get_datetime": get_datetime,
		"getdate": getdate,
		"add_months": add_months,
		"add_years": lambda day, n: day.replace(year=day.year + n),
		"add_to_date": lambda when, minutes=0: when + timedelta(minutes=minutes),
		"ZoneInfo": ZoneInfo,
		**extra,
	}
	tree_ = ast.parse(path.read_text(encoding="utf-8"))
	for node in tree_.body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") in names:
			exec(ast.unparse(node), space)
	for node in tree_.body:
		if isinstance(node, ast.FunctionDef) and node.name in names:
			exec(ast.unparse(node), space)
	return space


def _event(**kw):
	base = dict(
		starts_on=datetime(2026, 9, 7, 9, 0),
		ends_on=datetime(2026, 9, 7, 10, 0),
		repeat_this_event=0,
		repeat_on=None,
		repeat_till=None,
		owner="a@x",
		event_type="Private",
	)
	base.update(kw)
	return Row(base)


EVENTS = _load(CAL / "events.py", ("WEEKDAYS", "MOST_REPEATS", "occurrences", "whose"))


def test_a_single_event_is_on_the_days_it_spans():
	one = _event()
	assert len(EVENTS["occurrences"](one, date(2026, 9, 1), date(2026, 9, 30))) == 1
	assert EVENTS["occurrences"](one, date(2026, 9, 8), date(2026, 9, 30)) == []


def test_a_weekly_event_repeats_on_its_days_and_keeps_its_hour():
	one = _event(repeat_this_event=1, repeat_on="Weekly", monday=1, wednesday=1)
	found = EVENTS["occurrences"](one, date(2026, 9, 14), date(2026, 9, 20))
	assert [start for start, _end in found] == [datetime(2026, 9, 14, 9), datetime(2026, 9, 16, 9)]
	assert all(end - start == timedelta(hours=1) for start, end in found)


def test_a_weekly_event_with_no_day_ticked_repeats_on_its_own_weekday():
	one = _event(repeat_this_event=1, repeat_on="Weekly")  # 7 September 2026 is a Monday
	found = EVENTS["occurrences"](one, date(2026, 9, 1), date(2026, 9, 30))
	assert [start.day for start, _ in found] == [7, 14, 21, 28]


def test_a_repeat_stops_on_its_last_day_and_a_monthly_one_keeps_its_date():
	one = _event(repeat_this_event=1, repeat_on="Daily", repeat_till=date(2026, 9, 9))
	assert len(EVENTS["occurrences"](one, date(2026, 9, 1), date(2026, 9, 30))) == 3
	monthly = _event(repeat_this_event=1, repeat_on="Monthly")
	found = EVENTS["occurrences"](monthly, date(2026, 10, 1), date(2026, 12, 31))
	assert [start.date() for start, _ in found] == [date(2026, 10, 7), date(2026, 11, 7), date(2026, 12, 7)]


def test_an_event_is_mine_public_or_hidden_by_frappes_rule():
	whose = EVENTS["whose"]
	assert whose(_event(owner="me"), "me", False, False) == "mine"
	assert whose(_event(), "me", True, False) == "mine", "shared with me"
	assert whose(_event(), "me", False, True) == "mine", "I am a participant"
	assert whose(_event(event_type="Public"), "me", False, False) == "company"
	assert whose(_event(), "me", False, False) is None, "somebody's private event"


def test_an_event_about_a_record_is_shown_to_whoever_may_read_the_record():
	source = (CAL / "events.py").read_text()
	rows = source.split("def _rows(", 1)[1].split("\ndef ", 1)[0]
	assert "_can_read(pair, readable)" in rows and 'side, opens = "company", record' in rows
	assert 'frappe.has_permission(doctype, "read", doc=name)' in source


LAYERS = _load(CAL / "layers.py", ("SPAN", "entry"))


def test_an_entry_with_no_end_is_drawn_half_an_hour_and_an_all_day_one_to_the_next_day():
	layer = {"key": "k", "doctype": "Event", "color": "blue"}
	timed = LAYERS["entry"](layer, {"name": "E1", "start": "2026-09-24 10:00:00"})
	assert (timed["start"], timed["end"]) == ("2026-09-24T10:00:00", "2026-09-24T10:30:00")
	day = LAYERS["entry"](layer, {"name": "L1", "start": "2026-09-24", "end": "2026-09-26", "all_day": 1})
	assert (day["start"], day["end"]) == ("2026-09-24T00:00:00", "2026-09-27T00:00:00")


FEED = _load(CAL / "feed.py", ("LINE", "calendar", "utc", "escape", "fold", "slug"))


def test_the_ics_file_is_utc_dates_and_folded():
	found = [
		{"id": "k:E1", "title": "Call; Rana, about the quote", "start": "2026-09-24T10:00:00",
		 "end": "2026-09-24T11:00:00", "all_day": False, "doctype": "Event", "name": "E1", "description": "x" * 200},
		{"id": "k:L1", "title": "Annual Leave", "start": "2026-09-24T00:00:00",
		 "end": "2026-09-27T00:00:00", "all_day": True, "doctype": "Leave Application", "name": "L1"},
	]
	said = FEED["calendar"](found, "One · Rana", ZoneInfo("Asia/Dubai"), datetime(2026, 9, 23, 12), "https://acme.one")
	assert said.startswith("BEGIN:VCALENDAR\r\n") and said.endswith("END:VCALENDAR\r\n")
	assert "DTSTART:20260924T060000Z" in said, "10:00 in Dubai is 06:00 UTC"
	assert "DTSTART;VALUE=DATE:20260924\r\nDTEND;VALUE=DATE:20260927" in said
	assert "SUMMARY:Call\\; Rana\\, about the quote" in said
	assert "URL:https://acme.one/desk/leave-application/L1" in said
	assert all(len(line.encode()) <= 75 for line in said.split("\r\n"))


def test_folding_never_cuts_through_a_character():
	line = "SUMMARY:" + "مرحبا " * 30
	folded = FEED["fold"](line)
	assert folded.replace("\r\n ", "") == line
	assert all(len(piece.encode()) <= 75 for piece in folded.split("\r\n"))


def test_a_link_is_found_by_its_hash_kept_encrypted_and_read_as_its_owner():
	source = (CAL / "feed.py").read_text()
	assert '"token_hash": _hash(token)' in source and '{"token_hash": _hash(token or "")}' in source
	spec = json.loads((CAL / "doctype" / "calendar_feed" / "calendar_feed.json").read_text())
	assert next(f for f in spec["fields"] if f["fieldname"] == "token")["fieldtype"] == "Password"
	assert "allow_guest=True" in source and "@rate_limit(" in source
	assert "frappe.set_user(user)" in source
	for name in ("mine", "renew"):
		assert "frappe.session.user" in source.split(f"def {name}(", 1)[1].split("\ndef ", 1)[0]


def test_every_layer_is_declared_whole_and_registered():
	registered = re.findall(r'"(onedesk\.[\w.]+\.LAYERS)"', HOOKS.split("one_calendar_layers = [", 1)[1].split("]", 1)[0])
	assert len(registered) == 4
	keys = []
	for path in registered:
		module = tree.APP.joinpath(*path.split(".")[1:-1]).with_suffix(".py")
		source = module.read_text()
		layers_src = source.split("LAYERS = [", 1)[1].split("\n]\n", 1)[0]
		for one in re.findall(r"\{(.*?)\n\t\}", layers_src, re.S):
			key = re.search(r'"key": "([\w-]+)"', one).group(1)
			keys.append(key)
			assert re.search(r'"group": "(Mine|Workspace)"', one), key
			color = re.search(r'"color": "(\w+)"', one).group(1)
			assert color in {"blue", "cyan", "green", "orange", "purple", "pink", "red", "yellow", "gray", "teal", "violet", "amber"}, key
			rows = re.search(r'"rows": "([\w.]+)"', one).group(1)
			assert f"def {rows.rsplit('.', 1)[1]}(" in source, rows
	assert len(keys) == len(set(keys)), "a layer key is used twice"


def test_who_may_publish_is_one_list_in_both_halves():
	py = _load(CAL / "events.py", ("PUBLISHERS",))["PUBLISHERS"]
	js = (CAL / "page" / "onecalendar" / "onecalendar.js").read_text()
	listed = json.loads(re.search(r"CALENDAR_PUBLISHERS = (\[.*?\]);", js).group(1))
	assert tuple(listed) == py
	assert '"Event": {"validate": "onedesk.one_calendar.events.validate"}' in HOOKS


def test_nothing_is_copied_into_an_event():
	for path in [*CAL.glob("*.py"), tree.APP / "one_crm" / "calendar.py", tree.APP / "one_hr" / "calendar.py"]:
		said = path.read_text()
		assert '"doctype": "Event", "' not in said and 'new_doc("Event"' not in said, path.name
		assert ".insert(" not in said or path.name == "feed.py", path.name
