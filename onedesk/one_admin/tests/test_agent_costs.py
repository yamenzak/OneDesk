"""What the agents cost us on Cloudflare (one_admin/agent_costs.py): every
meter priced, the allowance shared as Cloudflare bills it, the cost growing
with the people, and the price list holding with it."""

import dataclasses
from unittest import mock

from onedesk.one_admin import agent_costs, costs, margins, plans, price_list


def test_every_meter_counted_is_priced_and_dated():
	assert set(agent_costs.counted(10)) == set(agent_costs.PRICES) == set(agent_costs.LABELS)
	assert agent_costs.READ_ON == "2026-11-13" and "13 November 2026" in agent_costs.__doc__
	assert all(one.usd > 0 and one.included > 0 for one in agent_costs.PRICES.values())


def test_the_allowance_is_shared_over_the_workspaces_that_pay_for_it():
	small = agent_costs.monthly(1)
	assert not small.lines["do_gb_s"] and not small.lines["do_requests"]
	alone = agent_costs.monthly(100, sharing=1)
	shared = agent_costs.monthly(100, sharing=costs.TENANTS_SHARING)
	assert alone.total < shared.total


def test_past_the_allowance_a_meter_costs_its_rate():
	price = agent_costs.PRICES["do_gb_s"]
	over = price.included / costs.TENANTS_SHARING + agent_costs.MILLION
	assert agent_costs.priced("do_gb_s", over, costs.TENANTS_SHARING) == costs.usd(price.usd)


def test_more_people_never_cost_less_and_an_agent_is_its_share():
	bills = [agent_costs.monthly(people) for people in (0, 5, 15, 40, 100, 400)]
	assert [one.total for one in bills] == sorted(one.total for one in bills)
	assert bills[3].per_agent() == round(bills[3].total / agent_costs.TYPICAL.agents, 4)
	assert agent_costs.seat() > 0


def test_a_credit_carries_most_at_the_cheapest_model():
	credit = price_list.ONECREDIT / price_list.MARKUP["ai"]
	worst = agent_costs.per_credit(credit)
	assert worst >= agent_costs.per_credit(credit, tier="balanced") > 0
	assert agent_costs.model_cost(tier=agent_costs.cheapest()) > 0


def test_a_plan_and_a_pack_count_their_agents():
	held = plans.Costs(agents=agent_costs.total, agent_seat=agent_costs.seat(), agent_credit=0.001)
	plan = plans.Offer("p", "P", "Plan", 100, seats=100)
	pack = plans.Offer("c", "C", "Credit Pack", 10, credits=1000)
	assert plans.agents(plan, held) == agent_costs.total(100)
	assert plans.cost(plan, held) == plans.agents(plan, held)
	assert plans.agents(pack, held) == 1.0


def test_the_biggest_pack_keeps_the_floor_once_agents_are_counted():
	pack = max(price_list.PACKS, key=lambda one: one.credits)
	assert not [one for one in margins.findings() if one.offer == pack.key]
	with mock.patch.object(price_list, "PACKS", tuple(dataclasses.replace(one, price=749) if one is pack else one for one in price_list.PACKS)):
		assert pack.key in [one.offer for one in margins.findings() if one.rule == "margin"]


def test_a_shorter_wake_costs_less():
	short = dataclasses.replace(agent_costs.TYPICAL, wake_seconds_a_message=5)
	assert agent_costs.a_message(short) < agent_costs.a_message()
