"""The credit arithmetic, read back without a site.

An accounting module, tested like one: every case is a table of buckets and an
expected answer, because the failures here are not exceptions. They are a
customer losing credits they paid for, or being given credits nobody paid for,
and both look like the code working.
"""

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree


def _credits():
	import importlib.util

	at = tree.APP / "one_admin" / "credits.py"
	spec = importlib.util.spec_from_file_location("onedesk_credits", at)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


credits = _credits()
Bucket, Draw = credits.Bucket, credits.Draw

TODAY = date(2026, 6, 1)
SOON = TODAY + timedelta(days=7)
LATER = TODAY + timedelta(days=90)
GONE = TODAY - timedelta(days=1)


def test_the_module_has_no_frappe_in_it():
	import ast

	body = ast.parse((tree.APP / "one_admin" / "credits.py").read_text(encoding="utf-8"))
	for node in ast.walk(body):
		if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef):
			node.body = [
				n
				for n in node.body
				if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant))
			]
	assert "frappe" not in ast.unparse(body)


# ------------------------------------------------------------------- balance


def test_nothing_granted_is_nothing_to_spend():
	assert credits.balance([], TODAY) == 0


def test_an_expired_grant_stops_counting_with_no_sweep_to_run():
	"""Expiry is arithmetic, not a nightly job. There is no expiry row to write
	and nothing to go wrong at three in the morning."""
	assert credits.balance([Bucket("a", 100, GONE)], TODAY) == 0
	assert credits.balance([Bucket("a", 100, TODAY)], TODAY) == 100


def test_the_day_it_expires_is_a_day_it_still_counts():
	"""Off by one here is a customer losing a day of credit they paid for."""
	assert credits.live([Bucket("a", 5, TODAY)], TODAY)
	assert not credits.live([Bucket("a", 5, TODAY)], TODAY + timedelta(days=1))


def test_an_empty_bucket_is_not_a_bucket():
	assert credits.live([Bucket("a", 0, LATER)], TODAY) == []


def test_an_overdraw_counts_and_does_not_expire():
	"""A bucket's date says when unspent credit stops being worth anything. An
	overdraw was never in a bucket: it is owed."""
	assert credits.balance([Bucket("a", 10, GONE)], TODAY, overdrawn=-4) == -4
	assert credits.balance([Bucket("a", 10, LATER)], TODAY, overdrawn=-4) == 6


# --------------------------------------------------------------------- order


def test_the_soonest_to_expire_is_drawn_first():
	"""The other order loses somebody credits they bought while a free monthly
	grant sits unused beside them, quietly, a month later."""
	buckets = [Bucket("bought", 100, LATER), Bucket("monthly", 10, SOON)]
	assert credits.draw(buckets, 4, TODAY) == [Draw("monthly", 4)]


def test_a_grant_that_never_expires_is_drawn_last():
	buckets = [Bucket("forever", 100, None), Bucket("dated", 10, LATER)]
	assert credits.draw(buckets, 12, TODAY) == [Draw("dated", 10), Draw("forever", 2)]


def test_a_draw_spans_as_many_buckets_as_it_needs():
	buckets = [Bucket("a", 3, SOON), Bucket("b", 3, LATER), Bucket("c", 100, None)]
	assert credits.draw(buckets, 7, TODAY) == [Draw("a", 3), Draw("b", 3), Draw("c", 1)]


def test_two_buckets_on_the_same_day_are_drawn_in_a_settled_order():
	"""Not for fairness — so that two runs of the same books agree."""
	buckets = [Bucket("b", 5, SOON), Bucket("a", 5, SOON)]
	assert [d.bucket for d in credits.draw(buckets, 6, TODAY)] == ["a", "b"]


def test_an_expired_bucket_is_never_drawn_from():
	buckets = [Bucket("old", 100, GONE), Bucket("new", 2, LATER)]
	assert credits.draw(buckets, 5, TODAY) == [Draw("new", 2), Draw(None, 3)]


# ------------------------------------------------------------------ overdraw


def test_what_nothing_covers_comes_back_belonging_to_nothing():
	"""Not an error here. Refusing at this point would be a call that already
	happened and was never charged for; the place to refuse is the hold."""
	assert credits.draw([], 5, TODAY) == [Draw(None, 5)]


def test_nothing_is_drawn_for_nothing():
	assert credits.draw([Bucket("a", 5, LATER)], 0, TODAY) == []
	assert credits.draw([Bucket("a", 5, LATER)], -1, TODAY) == []


# --------------------------------------------------------------------- holds


@pytest.mark.parametrize(
	"have,holding,want,yes",
	[
		(10, 0, 10, True),
		(10, 0, 11, False),
		(10, 6, 4, True),
		(10, 6, 5, False),
		(10, 10, 0.000001, False),
	],
)
def test_a_hold_is_spent_as_far_as_the_next_call_is_concerned(have, holding, want, yes):
	"""Two calls arriving together both seeing the same balance and both
	spending it is the race this exists to lose."""
	assert credits.enough([Bucket("a", have, LATER)], want, holding, TODAY) is yes


# ----------------------------------------------------------------- rounding


def test_a_thousandth_of_a_credit_is_not_rounded_away():
	"""A single call can cost that much. Rounding it to zero is a product given
	away by arithmetic."""
	buckets = [Bucket("a", 0.001, LATER)]
	assert credits.balance(buckets, TODAY) == 0.001
	assert credits.draw(buckets, 0.0005, TODAY) == [Draw("a", 0.0005)]


def test_a_draw_that_empties_a_bucket_leaves_no_crumb_behind_it():
	"""Floating point: 0.1 + 0.2 three times over should not leave 1e-17 in a
	bucket and then draw from it."""
	buckets = [Bucket("a", 0.3, SOON), Bucket("b", 10, LATER)]
	taken = credits.draw(buckets, 0.3, TODAY)
	assert taken == [Draw("a", 0.3)]
	assert sum(d.credits for d in taken) == 0.3
