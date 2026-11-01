"""Review stamps (one_interface/stamps.py): every screen the passthrough
has finished is named as frappe routes to it, with the day and the pass."""

import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from onedesk.one_interface import stamps  # noqa: E402


def test_every_passed_screen_is_named_with_its_day_and_pass():
	for screen, said in stamps.PASSED.items():
		assert stamps.SCREEN.match(screen), f"{screen}: name a screen as Form/<doctype>, List/<doctype> or a page's route"
		assert set(said) == {"on", "pass"}, f"{screen}: say `on` and `pass`, and nothing else"
		datetime.date.fromisoformat(said["on"])
		assert said["pass"].strip(), f"{screen}: say which pass finished it"


def test_screens_are_named_as_the_stamp_reads_them():
	for name in ("Form/Sales Invoice", "List/Customer", "query-report/General Ledger", "onemail"):
		assert stamps.SCREEN.match(name), name
	for name in ("Form/Sales Invoice/ACC-0001", "Form", "OneMail"):
		assert not stamps.SCREEN.match(name), name
