"""Points 6 and 7: a record on a page of its own (onedesk/one/tiers.py PAGES)
loses nothing its form has, and the workspace's extensions reach it."""

import importlib.util
import re
from pathlib import Path

import pytest

from onedesk.one import tiers

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "onedesk"
RECORD = (APP / "public" / "js" / "record.js").read_text()
FRAPPE = Path("/home/frappe/bench1/apps/frappe/frappe/public/js/frappe")

#: The island each page is drawn by.
ISLANDS = {"Project": ROOT / "frontend" / "src" / "project" / "ProjectPage.vue"}

#: frappe's dialogs a page opens on a record, and the form they are written against.
DIALOGS = (
	"form/sidebar/share.js",
	"views/communication.js",
	"form/linked_with.js",
	"form/reminders.js",
)


def _places():
	spec = importlib.util.spec_from_file_location("studio_places", APP / "one_studio" / "places.py")
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


def test_every_page_is_drawn_by_a_known_island():
	assert set(ISLANDS) == set(tiers.PAGES)


@pytest.mark.parametrize("doctype", sorted(tiers.PAGES))
def test_a_page_keeps_its_forms_menu_and_sidebar(doctype):
	"""The sidebar (assigned, tags, shared, likes, viewers, made and changed
	by) and frappe's own menu items, under the page's own."""
	source = ISLANDS[doctype].read_text()
	assert f'useRecord("{doctype}"' in source
	assert "<Record " in source
	assert "record.menu(" in source
	assert "follow(" in source, "the page hears the record saved, as a form does"
	for word in ("Print", "Email", "Show Links", "Duplicate", "Rename", "Delete", "Remind Me", "Copy to Clipboard"):
		assert f'__("{word}")' in RECORD, word
	assert "!!action.standard" in (APP / "public" / "js" / "island_page.js").read_text()


def test_the_record_handle_covers_what_frappes_dialogs_read():
	"""frappe's Share, Email, Links and Remind Me read a form; the handle
	record.js lends them must have every part of one they touch."""
	if not FRAPPE.exists():
		pytest.skip("frappe's source is not beside this checkout")
	handle = RECORD[RECORD.index("onedesk.record.handle =") : RECORD.index("onedesk.record.said =")]
	given = set(re.findall(r"^\t\t(\w+)[,:]", handle, re.M))
	read = set()
	for path in DIALOGS:
		read |= set(re.findall(r"\b(?:this|me)\.frm\??\.(\w+)", (FRAPPE / path).read_text()))
		read |= set(re.findall(r"\bfrm\??\.(\w+)", (FRAPPE / path).read_text()))
	# Read only by the sidebar part Share draws, which the page draws itself.
	unused = {"share_doc"}
	assert read - given - unused == set(), sorted(read - given - unused)


@pytest.mark.parametrize("doctype", sorted(tiers.PAGES))
def test_a_page_declares_its_places_and_fires_them(doctype):
	"""A Client Script reaches a form and a list, not a page of One's: the
	page says what an extension may hear on it, and fires it."""
	places = _places()
	source = ISLANDS[doctype].read_text()
	own = [place for place, one in places.PLACES.items() if one["record"] == doctype]
	assert own, f"no place for {doctype}'s page in one_studio/places.py"
	for place in own:
		for event in places.PLACES[place]["events"]:
			assert f'"{place}.{event}"' in source
	# What is written for the record's head runs on its page as well.
	assert '"record_head.drawn"' in source
