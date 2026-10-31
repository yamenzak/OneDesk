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


PACKS = _load(HERE / "packs.py", ("SEPARATORS", "THOUSANDS", "NUMBERS", "DIGITS_FROM", "_number", "pieces", "call"), re=re)


def test_a_ticket_is_said_from_pieces():
	pieces = PACKS["pieces"]
	assert pieces("A1828") == ["l:A", "n:1", "n:8", "n:2", "n:8"], "four digits are said one by one"
	assert pieces("A007") == ["l:A", "n:7"], "noughts in front are not said"
	assert pieces("b120") == ["l:B", "n:120"], "fewer are said whole"
	assert pieces("1828-3", "Whole Number") == ["n:1", "w:thousand", "n:828", "w:dash", "n:3"]
	assert pieces("2000", "Whole Number") == ["n:2", "w:thousand"]
	assert pieces("12", "Digit by Digit") == ["n:1", "n:2"]
	assert pieces("1828", "Whole Number", "ar") is None, "where thousands change the words, the sentence is recorded whole"
	assert pieces("ب12", lang="ar") == ["l:ب", "n:12"]
	assert PACKS["call"]("A1", "3") == ["w:ticket", "l:A", "n:1", "w:go_to", "c:3"]


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
		("TEXT", "LONG", "NUMBER", "CHECK", "COLOUR", "SELECT", "IMAGE", "CODE", "TYPES", "LOOK", "BRAND", "LOOKS", "LOOK_LABELS", "FIRST_LOOK", "COUNTDOWN", "ROTATING", "PROGRESS", "PRESETS"),
		_lt=lambda text, context=None: text,
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
				# a choice is a value, or a value with the name it is shown by
				offered = [one[0] if isinstance(one, tuple) else one for one in setting[4]]
				assert setting[3] in offered, f"{name}'s {setting[0]} starts on a choice it doesn't offer"
		width, height = one["size"]
		assert 0 < width <= 100 and 0 < height <= 100, name


def test_a_widget_draws_nothing_around_its_content():
	"""A widget is bare: its renderer in tv.js, and the styles it is drawn
	with, set no background, border, corners or font of their own. Those are
	its element's look, set in the editor and put on by tv.js `dress`; a look
	names only what an element may set, and every widget starts in one."""
	said = _widgets()
	tv = (ROOT / "onedesk/public/js/one_display/tv.js").read_text()
	renderers = tv[tv.index("var KINDS = {") : tv.index("function dayName")]
	found = re.findall(r"\bbox\.style\.(background|border\w*|fontFamily|padding|boxShadow)\b", renderers)
	assert not found, f"a renderer styles its own box: {found}"
	page = (ROOT / "onedesk/www/tv.html").read_text()
	for kind in (".panel", ".ticker", ".kiosk", ".weather", ".qr", ".custom"):
		for rule in re.findall(re.escape(kind) + r"\s*\{([^}]*)\}", page):
			assert not re.search(r"(^|;)\s*(background|border|border-radius|font-family|box-shadow)\s*:", rule), f"{kind} draws around its content: {rule}"
	for name, look in said["LOOKS"].items():
		assert set(look) <= set(said["LOOK"]), f"the {name} look sets what an element may not"
		assert name in said["LOOK_LABELS"], name
	assert set(said["FIRST_LOOK"]) <= set(said["TYPES"]) and set(said["FIRST_LOOK"].values()) <= set(said["LOOKS"])
	assert not {"Number", "List"} & set(said["TYPES"]), "a figure or a list is words with chips, not a widget"


def test_every_ready_made_widget_is_sound():
	"""A ready-made widget is a kind with settings it has, in a look there is,
	at a size that fits on a screen; none is named twice."""
	said = _widgets()
	keys = [one[0] for one in said["PRESETS"]]
	assert len(keys) == len(set(keys)), "a ready-made widget is named twice"
	assert not set(keys) & set(said["TYPES"]), "a ready-made widget is named as a kind"
	for key, kind, _label, settings, look, (width, height) in said["PRESETS"]:
		assert kind in said["TYPES"], f"{key} is a kind there isn't"
		allowed = {setting[0] for setting in said["TYPES"][kind]["settings"]}
		assert set(settings) <= allowed, f"{key} sets what a {kind} does not have: {set(settings) - allowed}"
		if "layout" in settings:
			layouts = next(setting[4] for setting in said["TYPES"][kind]["settings"] if setting[0] == "layout")
			assert settings["layout"] in [one[0] for one in layouts], f"{key} is drawn in a layout {kind} does not have"
		assert look in said["LOOKS"], f"{key} wears a look there isn't"
		assert 0 < width <= 100 and 0 < height <= 100, key


def test_every_premade_screen_has_its_picture():
	"""A template the gallery offers has a builder, a shape, a group the
	gallery shows, a picture of it, and puts down only ready-made widgets
	there are (starters.py)."""
	text = (HERE / "starters.py").read_text()
	groups = set(re.findall(r'^\t"(\w+)": _lt\(', text[text.index("GROUPS = {") : text.index("SHAPES = {")], re.M))
	rows = re.findall(r'^\t"(\w+)": \((\w+), "(wide|tall|strip)", "(\w+)",', text, re.M)
	assert len(rows) >= 24, "the library has its templates"
	presets = {one[0] for one in _widgets()["PRESETS"]} | set(_widgets()["TYPES"])
	for key, builder, _shape, group in rows:
		assert f"def {builder}(c: Canvas)" in text, f"{key} has no builder"
		assert group in groups, f"{key} is in a group the gallery does not show"
		assert (HERE.parent / "public/images/one_display/starters" / f"{key}.jpg").exists(), f"{key} has no picture"
	used = set(re.findall(r'c\.widget\("(\w+)"', text))
	assert used <= presets, f"a template puts down a widget there isn't: {used - presets}"


@pytest.mark.skipif(not shutil.which("node"), reason="no node to parse the player with")
def test_ready_made_code_runs_on_an_old_tvs_browser():
	"""A ready-made Custom widget's script runs in the screen's own browser."""
	acorn = ROOT / "frontend" / "node_modules" / "acorn"
	if not acorn.exists():
		pytest.skip("acorn is not installed")
	said = _widgets()
	for name in ("COUNTDOWN", "ROTATING", "PROGRESS"):
		code = said[name].replace("{words}", '["x"]')
		for script in re.findall(r"<script>(.*?)</script>", code, re.S):
			parsed = subprocess.run(["node", "-e", f"require({json.dumps(str(acorn))}).parse({json.dumps(script)}, {{ecmaVersion: 5}})"], capture_output=True, text=True)
			assert parsed.returncode == 0, f"{name} is not ES5: {parsed.stderr[-300:]}"


def test_every_layout_is_drawn_by_the_player():
	"""A kind's first layout is its renderer in tv.js KINDS; every other one
	it offers has its own renderer in LAYOUTS, so choosing it changes what is
	drawn and not only the box around it."""
	said = _widgets()
	tv = (ROOT / "onedesk/public/js/one_display/tv.js").read_text()
	block = tv[tv.index("var LAYOUTS = {") : tv.index("};", tv.index("var LAYOUTS = {"))]
	for kind, spec in said["TYPES"].items():
		layout = next((setting for setting in spec["settings"] if setting[0] == "layout"), None)
		if not layout:
			continue
		assert layout[3] == layout[4][0][0], f"{kind} starts on its first layout"
		line = next((one for one in block.splitlines() if one.strip().startswith((f'"{kind}":', f"{kind}:"))), "")
		for key, _label in layout[4][1:]:
			assert re.search(rf"\b{key}: \w+", line), f"{kind}'s {key} layout has no renderer in tv.js"


@pytest.mark.skipif(not shutil.which("node"), reason="no node to parse the player with")
def test_the_player_runs_on_an_old_tvs_browser():
	"""Chromium 53 on a 2017 TV parses ES5 and nothing newer."""
	acorn = ROOT / "frontend" / "node_modules" / "acorn"
	if not acorn.exists():
		pytest.skip("acorn is not installed")
	for path in ("onedesk/public/js/one_display/tv.js", "onedesk/public/js/one_display/worker.js", "onedesk/public/js/one_slide/play.js"):
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
def test_a_slide_is_drawn_safely_for_an_old_tv():
	"""The screen's renderer of a presentation's slide (public/js/one_slide/
	play.js): an 8-digit colour becomes rgba() for Chromium 53, a fade and a
	star are drawn as SVG, an attribute cannot be broken out of, an address
	that is not ours is dropped, and a hidden element is not drawn."""
	renderer = ROOT / "onedesk/public/js/one_slide/play.js"
	slide = {
		"background": "linear-gradient(90deg, #102030FF, #405060FF)",
		"elements": [
			{"id": "t", "type": "text", "left": 10, "top": 10, "width": 400, "content": '<p><span style="color: #FF000080">Hi</span></p>', "css": "text-shadow: 0 0 4px #000000FF", "transform": "rotate(5deg)"},
			{"id": "s", "type": "shape", "shapeType": "star", "left": 500, "top": 10, "width": 100, "height": 100, "fillColor": '#FF0000FF" onload="x', "fade": {"to": "#0000FFFF", "angle": 90}, "strokeColor": "#FFFFFFFF", "strokeWidth": 2},
			{"id": "i", "type": "image", "left": 0, "top": 0, "width": 50, "height": 50, "src": "javascript:alert(1)"},
			{"id": "p", "type": "image", "left": 0, "top": 0, "width": 50, "height": 50, "src": "/files/a.png", "crop": {"x": 0.1, "y": 0.1, "width": 0.5, "height": 0.5}},
			{"id": "h", "type": "text", "hidden": True, "content": "never drawn"},
		],
	}
	script = (
		"var window = {}; eval(require('fs').readFileSync(process.argv[1], 'utf8'));"
		"process.stdout.write(window.onedesk.play.slide(JSON.parse(process.argv[2])));"
	)
	ran = subprocess.run(["node", "-e", script, str(renderer), json.dumps(slide)], capture_output=True, text=True)
	assert ran.returncode == 0, ran.stderr[-400:]
	drawn = ran.stdout
	assert "rgba(255,0,0,0.502)" in drawn and "#FF000080" not in drawn and "rgba(0,0,0,1)" in drawn
	assert "linear-gradient(90deg, rgba(16,32,48,1), rgba(64,80,96,1))" in drawn
	assert "<polygon" in drawn and "linearGradient" in drawn and "onload" not in drawn
	assert "javascript" not in drawn and 'src="/files/a.png"' in drawn and "width:200%" in drawn
	assert "rotate(5deg)" in drawn and "never drawn" not in drawn


MOTION_TABLE = json.loads((ROOT / "onedesk/one_slide/motion.json").read_text())
CLEANED = _load(ROOT / "onedesk/one_slide/play.py", ("motion",), MOTION=MOTION_TABLE)


def test_the_player_moves_things_as_the_editor_does():
	"""play.js carries a copy of one_slide/motion.json, which the editor and
	the server read; the copy is the table, and a motion keeps only what the
	table names."""
	player = (ROOT / "onedesk/public/js/one_slide/play.js").read_text()
	copied = re.search(r"/\* motion \*/ (.*?) /\* end motion \*/", player).group(1)
	assert json.loads(copied) == MOTION_TABLE
	motion = CLEANED["motion"]
	assert motion({"wait": 2}) is None, "a motion that neither comes nor goes is none"
	kept = motion({"in": "Fly In", "from": "Up", "start": "Somehow", "wait": -3, "stay": 10_000, "speed": "fast", "again": 1, "colour": "red"})
	assert kept == {"in": "Fly In", "out": None, "from": "Left", "start": "With the Slide", "wait": 0.0, "stay": MOTION_TABLE["longest"], "speed": MOTION_TABLE["speed"], "again": True}
