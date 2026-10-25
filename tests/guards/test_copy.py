"""What a ready module shows is held to the copy rules (docs/WORDING.md,
OneInterface's limits; docs/READY.md, mechanism 1).

A heading (a tab, a panel, a dialog, a section, a group, a field's label) is
five words or fewer. A description is one sentence. No string says a word
on the banned list. Read from every module in onedesk/one/ready.py, ready or
on its way, so a module being made ready is held to them from the start.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from onedesk.one import ready  # noqa: E402

QUOTED = r"""(?:"((?:[^"\\]|\\.)*)"|'((?:[^'\\]|\\.)*)')"""
HEADING = re.compile(
	r"(?:\btitle|\bgroup|\blabel)\s*:\s*__\(\s*" + QUOTED
	+ r"""|:label="__\(\s*""" + QUOTED
	+ r"|\bheading(?:_with)?\(\s*__\(\s*" + QUOTED
)
DESCRIPTION = re.compile(
	r"\b(?:description|hint)\s*:\s*__\(\s*" + QUOTED + r"|\bheading(?:_with)?\(\s*__\([^)]*\)\s*,\s*__\(\s*" + QUOTED
)
SAID = re.compile(r"\b_{1,2}\(\s*" + QUOTED)
HEADING_WORDS = 5
BANNED = re.compile(
	r"\b(simply|just|easily|please|utili[sz]e|leverage|seamless(?:ly)?|powerful|robust|note that"
	r"|in order to|functionality|are you sure|something went wrong|frappe|erpnext)\b",
	re.I,
)


def _text(match: re.Match) -> str:
	return next((one for one in match.groups() if one is not None), "")


def _sentences(text: str) -> int:
	return len([one for one in re.split(r"(?<=[.!?])\s+", text.strip()) if one])


def _read():
	for module in ready.MODULES:
		for path in ready.files(module):
			if path.suffix in (".js", ".vue", ".py") and not path.name.startswith("test_"):
				yield module, path, path.read_text(encoding="utf-8")


def test_a_heading_is_five_words_or_fewer():
	found = [
		f"  {module} {path.name}: {_text(one)}"
		for module, path, text in _read()
		for one in HEADING.finditer(text)
		if len(_text(one).split()) > HEADING_WORDS
	]
	assert not found, "A heading is five words or fewer (docs/WORDING.md):\n" + "\n".join(found)


def test_a_description_is_one_sentence():
	found = [
		f"  {module} {path.name}: {_text(one)}"
		for module, path, text in _read()
		for one in DESCRIPTION.finditer(text)
		if _sentences(_text(one)) > 1
	]
	assert not found, "A description is one sentence (docs/WORDING.md):\n" + "\n".join(found)


def test_no_banned_word_is_shown():
	found = [
		f"  {module} {path.name}: {_text(one)}"
		for module, path, text in _read()
		for one in SAID.finditer(text)
		if BANNED.search(_text(one))
	]
	assert not found, "A word we never show (docs/WORDING.md):\n" + "\n".join(found)
