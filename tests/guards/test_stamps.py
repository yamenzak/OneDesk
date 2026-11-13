"""Review stamps (one_interface/stamps.py): every screen the passthrough
has finished is named as frappe routes to it, with the day and the pass."""

import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from onedesk.one_interface import stamps  # noqa: E402


def unstamped(passed: dict) -> list[str]:
	"""Each stamp misnamed, saying other than `on` and `pass`, on no real day
	or of no pass. Pure."""
	out = []
	for screen, said in passed.items():
		if not stamps.SCREEN.match(screen):
			out.append(f"{screen}: name a screen as Form/<doctype>, List/<doctype> or a page's route")
		if set(said) != {"on", "pass"}:
			out.append(f"{screen}: say `on` and `pass`, and nothing else")
			continue
		try:
			datetime.date.fromisoformat(said["on"])
		except (TypeError, ValueError):
			out.append(f"{screen}: {said['on']!r} is not a day")
		if not said["pass"].strip():
			out.append(f"{screen}: say which pass finished it")
	return out


def test_every_passed_screen_is_named_with_its_day_and_pass():
	found = unstamped(stamps.PASSED)
	assert not found, found


def test_the_stamp_rules_catch_their_examples():
	good = {"on": "2026-11-13", "pass": "the November pass"}
	assert unstamped({"Form/Task": good, "onemail": good}) == []
	found = unstamped({"OneMail": good, "List/Task": {"on": "13 Nov", "pass": " "}, "Form/Lead": {"on": "2026-11-13"}})
	assert len(found) == 4 and found[0].startswith("OneMail:")


def test_screens_are_named_as_the_stamp_reads_them():
	for name in ("Form/Sales Invoice", "List/Customer", "query-report/General Ledger", "onemail"):
		assert stamps.SCREEN.match(name), name
	for name in ("Form/Sales Invoice/ACC-0001", "Form", "OneMail"):
		assert not stamps.SCREEN.match(name), name
