"""What One sells makes money and makes sense (one_admin/price_list.py,
costs.py, margins.py): nothing under the margin floor at its worst, no plan
too big for a shared server without its own, every key versioned once."""

import dataclasses
from unittest import mock

from onedesk.one_admin import price_list, costs, margins


def test_nothing_sold_loses_money_or_makes_no_sense():
	said = margins.findings()
	assert not said, "\n".join(one.said for one in said)


def test_the_floor_catches_a_plan_sold_under_cost():
	cheap = dataclasses.replace(price_list.PLANS[0], price=20)
	with mock.patch.object(price_list, "PLANS", (cheap, *price_list.PLANS[1:])):
		assert [one.rule for one in margins.findings() if one.offer == cheap.key] == ["margin"]


def test_a_plan_too_big_to_share_a_server_needs_its_own():
	big = dataclasses.replace(price_list.PLANS[-1], own_server=False)
	with mock.patch.object(price_list, "PLANS", (*price_list.PLANS[:-1], big)):
		assert "fits" in [one.rule for one in margins.findings() if one.offer == big.key]


def test_every_key_is_versioned_and_sold_once():
	keys = [one.key for one in (*price_list.PLANS, *price_list.ADDONS, *price_list.PACKS)]
	assert all("@" in key for key in keys) and len(keys) == len(set(keys))
	selling = [price_list.family(one.key) for group in price_list.selling() for one in group]
	assert len(selling) == len(set(selling)), "two versions of one thing on sale at once"


def test_stripe_takes_its_worst_and_a_credit_is_worth_its_dirhams():
	assert costs.stripe_fee(100) == round(100 * 0.056 + 1, 4)
	assert costs.stripe_fee(100, worst=False) == round(100 * 0.036 + 1, 4)
	assert price_list.credits_per_dollar() == round(3.6725 / 0.04, 4)
	assert price_list.yearly(109) == 1090
