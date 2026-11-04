"""A person keeps their mailbox: the nightly job that ends a leave cover
ends only cover rows."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree


def test_the_cover_job_ends_only_cover_rows():
	"""frappe reads an empty date as the earliest day, so `<` alone on the
	cover date matched every holder's own row: each night everybody lost
	their mailbox (until 5 November 2026). The job asks for a cover date
	first."""
	source = (tree.APP / "one_mail" / "rules.py").read_text(encoding="utf-8")
	body = source.split("def cover(", 1)[1].split("\ndef ", 1)[0]
	assert '["one_cover_until", "is", "set"]' in body and 'filters={"one_cover_until": ["<"' not in body


def test_nothing_reaches_into_frappe_local_by_its_dict():
	"""frappe.local is a context variable since 3 November 2026 and has no
	__dict__: reaching for it stopped every mail One sends."""
	found = [
		str(path.relative_to(tree.APP))
		for path in tree.APP.rglob("*.py")
		if "local.__dict__" in path.read_text(encoding="utf-8")
	]
	assert not found, found

