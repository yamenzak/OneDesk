"""OneDisplay: the parts a screen depends on that need no site, read from
their own files: when a schedule's row covers a moment, how a ticket is said,
which fields a mapping names and how a line is filled, a recording wrapped as
a WAV, every widget's declaration, and the player still running on an old
TV's browser."""

import ast
import base64
import io
import json
import re
import shutil
import subprocess
import wave
from datetime import datetime, time, timedelta
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[1]


def _load(path: Path, names: tuple, **extra) -> dict:
	space = dict(extra)
	for node in ast.parse(path.read_text()).body:
		if isinstance(node, ast.Assign):
			target = node.targets[0]
			named = [one.id for one in target.elts] if isinstance(target, ast.Tuple) else [getattr(target, "id", "")]
			if set(named) & set(names):
				exec(ast.unparse(node), space)
		if isinstance(node, ast.FunctionDef) and node.name in names:
			exec(ast.unparse(node), space)
	return space


def _time(value) -> time:
	return value if isinstance(value, time) else datetime.strptime(value, "%H:%M:%S").time()


PROGRAMME = _load(HERE / "programme.py", ("DAYS", "_within", "_spoken"), get_time=_time, timedelta=timedelta, datetime=datetime, re=re)
WITHIN = PROGRAMME["_within"]
MONDAY = datetime(2026, 10, 26)


class Row(dict):
	"""A schedule's row as frappe hands it: its fields as attributes."""

	__getattr__ = dict.get


def _at(day: int, hour: int, minute: int = 0) -> datetime:
	return MONDAY + timedelta(days=day, hours=hour, minutes=minute)


def test_a_row_covers_its_days_between_its_times():
	row = Row(days="Weekdays", from_time="09:00:00", to_time="17:00:00")
	assert WITHIN(row, _at(0, 9))
	assert WITHIN(row, _at(4, 16, 59))
	assert not WITHIN(row, _at(0, 17)), "the end is not inside"
	assert not WITHIN(row, _at(5, 12)), "Saturday is the weekend"
	assert WITHIN(Row(days="Weekend"), _at(6, 3)), "a row with no times takes the whole day"


def test_a_row_that_ends_before_it_starts_runs_across_midnight():
	night = Row(days="Friday", from_time="22:00:00", to_time="07:00:00")
	assert WITHIN(night, _at(4, 23))
	assert WITHIN(night, _at(5, 6, 59)), "Friday's night goes on into Saturday's morning"
	assert not WITHIN(night, _at(4, 6)), "Friday's morning belongs to Thursday's night"
	assert not WITHIN(night, _at(5, 23))


def test_a_ticket_is_said_without_its_noughts():
	spoken = PROGRAMME["_spoken"]
	assert spoken("A007") == "A 7"
	assert spoken("B120") == "B 120"
	assert spoken("17") == "17"


SOURCES = _load(HERE / "sources.py", ("FIELD", "fields_in", "_line"), re=re)


def test_a_mapping_names_the_fields_it_shows():
	fields_in = SOURCES["fields_in"]
	assert fields_in({"title": "{customer} owes {grand_total}", "subtitle": "status"}) == {"customer", "grand_total", "status"}
	assert fields_in({"text": "Welcome to the showroom!"}) == set(), "words are not a field"
	assert fields_in({}) == set()


def test_a_line_is_filled_from_a_row():
	line = SOURCES["_line"]
	row = {"customer": "Gulf Glass", "status": "Open"}
	assert line("{customer}: {status}", row) == "Gulf Glass: Open"
	assert line("status", row) == "Open"
	assert line("{missing} days", row) == "days"
	assert line("Plain words", row) == "Plain words"


def test_a_recording_is_wrapped_as_a_wav():
	wrap = _load(HERE / "voices.py", ("_wav",), base64=base64, io=io, re=re, wave=wave)["_wav"]
	pcm = b"\x00\x01" * 2400
	made = wrap(base64.b64encode(pcm).decode(), "audio/L16;codec=pcm;rate=24000")
	with wave.open(io.BytesIO(made)) as sound:
		assert (sound.getnchannels(), sound.getsampwidth(), sound.getframerate(), sound.getnframes()) == (1, 2, 24000, 2400)
	assert wrap(base64.b64encode(made).decode(), "audio/wav") == made, "a WAV stays as it is"


def _widgets() -> dict:
	return _load(
		HERE / "widgets.py",
		("TEXT", "LONG", "NUMBER", "CHECK", "COLOUR", "SELECT", "IMAGE", "CODE", "TYPES"),
		_lt=str,
	)


def test_every_widget_is_declared_soundly():
	said = _widgets()
	kinds = {said[name] for name in ("TEXT", "LONG", "NUMBER", "CHECK", "COLOUR", "SELECT", "IMAGE", "CODE")}
	source = json.loads((HERE / "doctype" / "display_source" / "display_source.json").read_text())
	allowed = set(next(f for f in source["fields"] if f["fieldname"] == "kind")["options"].split("\n"))
	widget = json.loads((HERE / "doctype" / "display_widget" / "display_widget.json").read_text())
	offered = set(next(f for f in widget["fields"] if f["fieldname"] == "widget_type")["options"].split("\n")) - {""}
	assert set(said["TYPES"]) == offered, "the widget's Type offers every kind declared, and only those"
	for name, one in said["TYPES"].items():
		assert {"label", "about", "sources", "slots", "settings", "size"} <= set(one), name
		assert set(one["sources"]) <= allowed, f"{name} names a source kind there isn't"
		keys = [setting[0] for setting in one["settings"]]
		assert len(keys) == len(set(keys)), f"{name} names a setting twice"
		for setting in one["settings"]:
			assert setting[1] in kinds, f"{name}'s {setting[0]} is drawn as {setting[1]}"
			if setting[1] == said["SELECT"]:
				assert setting[3] in setting[4], f"{name}'s {setting[0]} starts on a choice it doesn't offer"
		width, height = one["size"]
		assert 0 < width <= 100 and 0 < height <= 100, name


@pytest.mark.skipif(not shutil.which("node"), reason="no node to parse the player with")
def test_the_player_runs_on_an_old_tvs_browser():
	"""Chromium 53 on a 2017 TV parses ES5 and nothing newer."""
	acorn = ROOT / "frontend" / "node_modules" / "acorn"
	if not acorn.exists():
		pytest.skip("acorn is not installed")
	for path in ("onedesk/public/js/one_display/tv.js", "onedesk/public/js/one_display/worker.js", "onedesk/public/js/one_display/blocks.js"):
		parsed = subprocess.run(
			["node", "-e", f"require({json.dumps(str(acorn))}).parse(require('fs').readFileSync({json.dumps(str(ROOT / path))}, 'utf8'), {{ecmaVersion: 5}})"],
			capture_output=True,
			text=True,
		)
		assert parsed.returncode == 0, f"{path} is not ES5: {parsed.stderr[-400:]}"


def test_a_songs_length_is_read_from_its_file():
	"""A track nobody's browser measured still plays, so the server reads its
	length: a WAV from its header, an MP3 from its bitrate."""
	import base64
	import io
	import wave

	seconds = _load(HERE / "make.py", ("BITRATES", "RATES", "seconds"), base64=base64)["seconds"]

	sound = io.BytesIO()
	with wave.open(sound, "wb") as written:
		written.setnchannels(1)
		written.setsampwidth(2)
		written.setframerate(8000)
		written.writeframes(b"\x00\x00" * 8000 * 2)
	assert seconds({"data": base64.b64encode(sound.getvalue()).decode()}) == 2.0
	frame = bytes([0xFF, 0xFB, 0x90, 0x64]) + b"\x00" * 413
	assert seconds({"data": base64.b64encode(b"ID3\x03\x00\x00\x00\x00\x00\x00" + frame * 300).decode()}) == round(417 * 300 * 8 / 128000, 1)
	assert seconds({"data": base64.b64encode(b"nothing to hear").decode()}) == 0.0


@pytest.mark.skipif(not shutil.which("node"), reason="no node to run the renderer with")
def test_a_designed_slide_is_drawn_safely_for_an_old_tv():
	"""The one renderer the screen and the designer share: what a person typed
	is escaped, a see-through colour becomes rgba() for Chromium 53, nothing
	uses `inset`, a star is drawn as a shape, and CSS that loads something is
	dropped even if it reached the renderer."""
	renderer = ROOT / "onedesk/public/js/one_display/blocks.js"
	design = {
		"background": "#0e6e8c",
		"background2": "#00000080",
		"blocks": [
			{"id": "t", "kind": "text", "x": 5, "y": 5, "w": 50, "h": 20, "text": "<script>alert(1)</script>", "rotate": 10, "valign": "middle", "fill": "#ffffff33", "shadow_colour": "#000", "css": "color: red; background: url(x)"},
			{"id": "s", "kind": "shape", "shape": "star", "x": 60, "y": 5, "w": 20, "h": 20, "fill": "#ff0000", "fill2": "#0000ff", "stroke": 4, "stroke_colour": "#fff"},
			{"id": "h", "kind": "text", "hidden": 1, "text": "never drawn"},
		],
	}
	script = (
		"var window = {}; eval(require('fs').readFileSync(process.argv[1], 'utf8'));"
		"process.stdout.write(window.onedesk.blocks.slide(JSON.parse(process.argv[2]), {}));"
	)
	ran = subprocess.run(["node", "-e", script, str(renderer), json.dumps(design)], capture_output=True, text=True)
	assert ran.returncode == 0, ran.stderr[-400:]
	drawn = ran.stdout
	assert "<script>" not in drawn and "&lt;script&gt;" in drawn
	assert "rgba(0,0,0,0.502)" in drawn and "rgba(255,255,255,0.2)" in drawn and "#00000080" not in drawn
	assert "inset" not in drawn and "rotate(10deg)" in drawn and "justify-content:center" in drawn
	assert "<polygon" in drawn and "linearGradient" in drawn
	assert "color:red" in drawn and "url(x)" not in drawn
	assert "never drawn" not in drawn
