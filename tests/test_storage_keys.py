"""What a workspace may name, read back without a site.

`onedesk/one_admin/keys.py` imports nothing of Frappe or boto3 for this reason.
A mistake here is one customer reading another customer's files, and it would
not show up in any test that needed a bucket.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from onedesk.one_admin import keys


def test_a_workspace_owns_one_prefix():
	assert keys.prefix("acme") == "tenants/acme/"


def test_an_ordinary_key_lands_under_it():
	assert keys.under("acme", "files/invoice.pdf") == "tenants/acme/files/invoice.pdf"


@pytest.mark.parametrize(
	"escape",
	[
		"../other/secret.pdf",
		"a/../../other/secret.pdf",
		"..",
		"a/..",
		"../..",
		"files/../../../etc/passwd",
	],
)
def test_nothing_climbs_out_of_the_prefix(escape):
	with pytest.raises(keys.Unnameable):
		keys.under("acme", escape)


def test_a_dotdot_inside_the_prefix_is_still_refused():
	"""`a/../b` lands on `b` and is harmless. It is refused anyway.

	Nobody legitimate sends one, and a rule that is easy to verify beats a rule
	that is merely correct.
	"""
	with pytest.raises(keys.Unnameable):
		keys.under("acme", "a/../b")


@pytest.mark.parametrize("absolute", ["/etc/passwd", "/tenants/other/x"])
def test_an_absolute_key_is_refused(absolute):
	with pytest.raises(keys.Unnameable):
		keys.under("acme", absolute)


@pytest.mark.parametrize("nasty", ["a\\b", "a\x00b", "a\nb", "a\rb"])
def test_a_backslash_or_a_control_character_is_refused(nasty):
	with pytest.raises(keys.Unnameable):
		keys.under("acme", nasty)


@pytest.mark.parametrize("empty", ["", "   ", ".", "./"])
def test_nothing_is_not_a_key(empty):
	with pytest.raises(keys.Unnameable):
		keys.under("acme", empty)


def test_a_slug_with_a_slash_in_it_is_not_a_workspace():
	"""Otherwise a tenant named `a/../b` owns somebody else's prefix."""
	with pytest.raises(keys.Unnameable):
		keys.prefix("acme/../other")


def test_a_key_longer_than_s3_allows_is_refused_here():
	with pytest.raises(keys.Unnameable):
		keys.under("acme", "x" * (keys.LONGEST + 1))


def test_redundant_separators_are_tidied_rather_than_refused():
	assert keys.under("acme", "files//./invoice.pdf") == "tenants/acme/files/invoice.pdf"


def test_owning_is_the_read_side_of_naming():
	full = keys.under("acme", "files/invoice.pdf")
	assert keys.owns("acme", full)
	assert not keys.owns("other", full)
	assert not keys.owns("acme", "tenants/acmeish/files/invoice.pdf")


def test_a_neighbour_with_a_longer_name_is_not_inside_us():
	"""`tenants/acme/` must not be a prefix of `tenants/acme2/...`."""
	assert not keys.owns("acme", "tenants/acme2/secret.pdf")


def test_room_is_what_was_measured_plus_what_was_promised():
	assert keys.room_for(held=100, pending=10, limit=200, wanted=90)
	assert not keys.room_for(held=100, pending=10, limit=200, wanted=91)


def test_a_plan_with_no_storage_line_is_unmetered_rather_than_nothing():
	"""Refusing every upload because nobody set a limit is the worse answer."""
	assert keys.room_for(held=10**12, pending=0, limit=0, wanted=10**9)
	assert keys.room_for(held=0, pending=0, limit=-1, wanted=10**9)
