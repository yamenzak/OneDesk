"""The price list and the calculator over it, read back without a site.

A price list is wrong in a way nothing raises: a plan nobody would move up
to, an add-on nobody would buy, a price under what it costs us. The
calculator (one_admin/plans.py) says which, and these hold the list the
admin site starts with (one_admin/offerings.py) to it.
"""

import ast
import importlib.util
import sys
from itertools import pairwise
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree


def _plans():
	spec = importlib.util.spec_from_file_location("onedesk_plans", tree.APP / "one_admin" / "plans.py")
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


plans = _plans()


def _literal(name):
	"""A constant from offerings.py, read without importing frappe."""
	source = (tree.APP / "one_admin" / "offerings.py").read_text(encoding="utf-8")
	for node in ast.parse(source).body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", None) == name:
			return ast.literal_eval(node.value)
	raise AssertionError(f"offerings.py has no {name}")


def _list():
	ladder = [
		plans.Offer(
			key,
			label,
			"Plan",
			price,
			seats=seats,
			storage_gb=storage,
			database_gb=database,
			credits_a_month=credits,
		)
		for key, label, price, seats, storage, database, credits, _trial in _literal("PLANS")
	]
	sold = [
		plans.Offer(key, label, "Add-on", price, **adds) for key, label, price, adds in _literal("ADDONS")
	]
	sold += [
		plans.Offer(key, label, "Credit Pack", price, credits=credits)
		for key, label, price, credits in _literal("PACKS")
	]
	held = _literal("COSTS")
	costs = plans.Costs(
		workspace=held["cost_workspace"],
		seat=held["cost_seat"],
		storage_gb=held["cost_storage_gb"],
		database_gb=held["cost_database_gb"],
		backup_gb=held["cost_backup_gb"],
		backups_kept=held["backups_kept"],
		# A dollar of provider cost is 1,000 credits, marked up twice.
		credit=1 / 2000,
		margin=held["least_margin"],
	)
	return ladder, sold, costs


def test_the_price_list_we_start_with_makes_sense():
	ladder, sold, costs = _list()
	assert len(ladder) == 4 and min(one.price for one in ladder) == 30
	found = plans.check(ladder, sold, costs)
	assert not found, [one.said for one in found]


def test_every_database_and_storage_size_is_sold():
	_ladder, sold, _costs = _list()
	for resource in ("storage_gb", "database_gb", "seats", "credits_a_month"):
		assert any(one.resource == resource for one in sold), resource
	assert min(one.database_gb for one in _list()[0]) >= 1, "every plan carries at least a GB of database"


def test_moving_up_beats_add_ons_and_a_little_more_is_an_add_on():
	ladder, sold, _costs = _list()
	for lower, upper in pairwise(ladder):
		assert plans.upgrade_saving(lower, upper, sold) > 0.3, (lower.label, upper.label)
	# Two more GB of database on the smallest plan is an add-on...
	cheapest = plans.quote({"seats": 5, "database_gb": 3}, ladder, sold)[0]
	assert cheapest.plan.key == "starter" and cheapest.extras
	# ...and three times the seats as well is the next plan.
	cheapest = plans.quote({"seats": 15, "database_gb": 3}, ladder, sold)[0]
	assert cheapest.plan.key == "team" and not cheapest.extras


def test_the_check_catches_what_does_not_make_sense():
	ladder, sold, costs = _list()
	# A plan up the ladder that is dearer than its add-ons nobody moves to.
	dear = [
		*ladder[:-1],
		plans.Offer(
			"scale", "Scale", "Plan", 5000, seats=100, storage_gb=1000, database_gb=15, credits_a_month=20000
		),
	]
	assert any(one.level == "red" and one.offer == "scale" for one in plans.check(dear, sold, costs))
	# A price under what it costs us.
	cheap = [
		plans.Offer("starter", "Starter", "Plan", 5, seats=5, storage_gb=20, database_gb=1, credits_a_month=1000),
		*ladder[1:],
	]
	assert any(one.level == "red" and one.offer == "starter" for one in plans.check(cheap, sold, costs))
	# A plan that gives less than the one below it.
	fewer = [
		ladder[0],
		plans.Offer("team", "Team", "Plan", 70, seats=4, storage_gb=100, database_gb=3, credits_a_month=3000),
		*ladder[2:],
	]
	assert any(one.offer == "team" and "fewer" in one.said for one in plans.check(fewer, sold, costs))


def test_add_ons_are_bought_in_the_cheapest_mix():
	_ladder, sold, _costs = _list()
	# 300 GB is one 250 and one 50, not two 250s.
	mix = plans.extras_for("storage_gb", 300, sold)
	assert sorted((one.key, count) for one, count in mix) == [("storage-250", 1), ("storage-50", 1)]
	assert plans.topping("database_gb", 0, sold) == 0


def test_zero_on_a_plan_is_no_limit():
	unlimited = plans.Offer("any", "Any", "Plan", 100)
	assert unlimited.quota("storage_gb") == plans.INF
	assert unlimited.quota("credits_a_month") == 0
