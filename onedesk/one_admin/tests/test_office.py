"""What a conversion in the office containers costs and is billed (one_admin/office.py)."""

from onedesk.one_admin import office


def test_a_conversion_costs_its_seconds_and_the_idle_tail():
	assert round(office.cost(0), 5) == round(office.IDLE_AFTER * office.RUNNING, 5)
	assert office.cost(10) > office.cost(0)


def test_it_is_billed_at_least_one_credit_and_rounded_up():
	assert office.credits(3, 1.5, 100) == 1
	assert office.credits(3, 0, 0) == 1
	assert office.credits(office.WAIT, 1.5, 100) == 1, "the longest a conversion may take still costs one credit"
	assert office.credits(3, 1.5, 10_000) > 1


def test_the_rates_are_cloudflare_standard_1():
	hour = 3600 * (office.RUNNING + office.WORKING)
	assert 0.07 < hour < 0.08
	assert 0.03 < 3600 * office.RUNNING < 0.04
