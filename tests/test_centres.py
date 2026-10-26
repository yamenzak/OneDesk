"""Settings is gone (docs/ONE.md, stages 2 and 3): each section it had is a
tab of the centre or module it belongs to, drawn by a CenterSection and
loaded and saved through that module. Pure parts."""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

JS = tree.APP / "public" / "js"

MOVED = {
	"draw_general(": (JS / "one_control.js", tree.APP / "one" / "control.py"),
	"draw_holidays(": (JS / "one_hr" / "hr_control.js", tree.APP / "one_hr" / "control.py"),
	"draw_link(": (JS / "one_calendar" / "calendar_control.js", tree.APP / "one_calendar" / "control.py"),
	"draw_reads(": (JS / "one_ai" / "ai_center.js", tree.APP / "one_ai" / "yours.py"),
	"draw_access(": (JS / "access_center.js", tree.APP / "one" / "access_center.py"),
	"draw_numbering(": (JS / "one_studio" / "studio_control.js", tree.APP / "one_studio" / "control.py"),
	"draw_printing(": (JS / "one_studio" / "studio_control.js", tree.APP / "one_studio" / "control.py"),
	"draw_approvals(": (JS / "one_studio" / "studio_control.js", tree.APP / "one_studio" / "control.py"),
	"draw_words(": (JS / "notification_center.js", tree.APP / "one" / "notification_words.py"),
}


def test_what_moved_out_is_drawn_in_its_centre():
	for drawn, (script, server) in MOVED.items():
		source = script.read_text()
		assert drawn in source and "extends onedesk.CenterSection" in source, script
		assert "def load(" in server.read_text(), server
	assert not (tree.APP / "one" / "settings.py").exists()
	assert not (JS / "settings.js").exists()
	for page in ("settings", "workspace_settings"):
		assert not (tree.APP / "one" / "page" / page).exists(), page


def test_every_workspace_section_is_for_its_administrators():
	for server in (
		tree.APP / "one" / "control.py",
		tree.APP / "one_hr" / "control.py",
		tree.APP / "one_studio" / "control.py",
		tree.APP / "one" / "notification_words.py",
		tree.APP / "one" / "access_center.py",
	):
		source = server.read_text()
		body = source[source.index("def load(") :]
		body = body[: body.index("\n\n\n")]
		assert "roles.require()" in body, server


def test_no_rail_opens_a_settings_page():
	for rail in tree.APP.glob("*/sidebar/*/*.json"):
		items = json.loads(rail.read_text())["items"]
		assert not any(one.get("link_to") in ("settings", "workspace-settings") for one in items), rail


def test_a_section_sends_every_field_and_behaves_like_a_form():
	engine = (JS / "center_section.js").read_text()
	shell = (JS / "shell.js").read_text()
	assert "extends onedesk.shell.Editor" in engine
	for source in (engine, shell):
		assert "get_values(" not in source, "FieldGroup.get_values leaves a cleared field out, so it would never be cleared"
	for part in ("doc_subscribe", "doc_update", "beforeunload", "TimestampMismatchError", "save_action"):
		assert part in shell, part


def test_what_oneai_offers_is_for_a_tab_that_exists():
	"""OneAI's suggestions on a centre's tab are keyed by the page the tab
	tells it (module_settings.js `activate`, CenterSection.HERE)."""
	ai = (tree.APP / "one" / "ai.py").read_text()
	assert not re.findall(r'"page:(?:settings|workspace-settings)/', ai), "OneAI offers something on the old Settings pages"
	for key in ("one/general", "onestudio/numbering", "onestudio/printing", "onestudio/approvals", "notifications/words", "access/access", "onehr/holidays"):
		assert f'"page:{key}"' in ai, key
