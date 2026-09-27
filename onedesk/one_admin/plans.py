"""What a plan and an add-on cost us, what they sell for, and whether the
price list makes sense. No frappe in it: the report, the proxy and the tests
all hand it plain rows.

A workspace is sold four things it can run out of: **seats**, **storage** (its
files, in R2), **database** (its site's database on Frappe Cloud, and the
backups kept of it) and **OneAI credits**. A plan is a bundle of all four at a
monthly price. An add-on is one of them, in a fixed size, on top of a plan.

**Why a calculator.** A price list is only coherent if three things hold at
once, and they pull against each other:

1. every price covers what it costs us, with the margin we want
   (`margin`);
2. a plan is a better deal than buying its contents as add-ons, and more so
   the bigger it is, so somebody who needs a lot more moves up
   (`upgrade`);
3. an add-on is a better deal than moving up for somebody who needs a
   little more, or nobody would buy one (`addon`).

Change one price and the other two can quietly stop holding. `check` says
which, and `quote` answers the customer's version of the same question: given
what I need, which plan with which add-ons is cheapest.

Credits in a plan are monthly and do not roll over; credits bought in a pack
never expire (topup.py). A plan's monthly credits are valued at what the same
credits cost in packs, since that is what a customer would otherwise pay.
"""

from dataclasses import dataclass, field
from itertools import pairwise
from math import ceil

#: The four things a workspace can run out of, as Offering fields.
RESOURCES = ("seats", "storage_gb", "database_gb", "credits_a_month")

#: What a plan leaves at zero to mean no limit; zero credits are none.
UNLIMITED_AT_ZERO = ("seats", "storage_gb", "database_gb")
INF = float("inf")

#: What each resource is called, for a finding a person reads.
NAMED = {
	"seats": "seats",
	"storage_gb": "GB of storage",
	"database_gb": "GB of database",
	"credits_a_month": "credits a month",
}


@dataclass
class Costs:
	"""What one of each thing costs us a month, in the offerings' currency."""

	workspace: float = 0.0  # a workspace before any size: its site, its mail
	seat: float = 0.0
	storage_gb: float = 0.0
	database_gb: float = 0.0  # the database itself, on the site's plan
	backup_gb: float = 0.0  # one backup copy of one GB, kept a month
	backups_kept: int = 0
	credit: float = 0.0
	margin: float = 2.0  # the least a price may be over what it costs us


@dataclass
class Offer:
	key: str
	label: str
	kind: str  # Plan, Add-on or Credit Pack
	price: float
	seats: int = 0
	storage_gb: float = 0
	database_gb: float = 0
	credits_a_month: int = 0
	credits: int = 0  # a pack's, once

	def quota(self, resource: str) -> float:
		held = float(getattr(self, resource) or 0)
		# A plan's zero seats, storage or database is no limit (Offering).
		if not held and self.kind == "Plan" and resource in UNLIMITED_AT_ZERO:
			return INF
		return held

	@property
	def resource(self) -> str | None:
		"""What an add-on or a pack adds. One thing each, so it can be
		multiplied by how many are bought."""
		if self.kind == "Credit Pack":
			return "credits_a_month"
		held = [one for one in RESOURCES if self.quota(one)]
		return held[0] if len(held) == 1 else None

	@property
	def size(self) -> float:
		return float(self.credits) if self.kind == "Credit Pack" else self.quota(self.resource)


@dataclass
class Finding:
	level: str  # "red" when the list does not make sense, "orange" when it is close
	offer: str
	said: str


@dataclass
class Option:
	"""One way to get what a customer needs: a plan and what goes on it."""

	plan: Offer
	extras: list[tuple[Offer, int]] = field(default_factory=list)
	unmet: list[str] = field(default_factory=list)

	@property
	def monthly(self) -> float:
		return round(self.plan.price + sum(one.price * count for one, count in self.extras), 2)


def cost(offer: Offer, costs: Costs) -> float:
	"""What an offering costs us a month; a pack's once."""
	if offer.kind == "Credit Pack":
		return round(offer.credits * costs.credit, 4)
	database = costs.database_gb + costs.backup_gb * costs.backups_kept
	return round(
		(costs.workspace if offer.kind == "Plan" else 0)
		+ offer.seats * costs.seat
		+ offer.storage_gb * costs.storage_gb
		+ offer.database_gb * database
		+ offer.credits_a_month * costs.credit,
		4,
	)


def extras_for(resource: str, amount: float, sold: list[Offer]) -> list[tuple[Offer, int]]:
	"""The cheapest add-ons (or packs, for credits) that make up `amount`.

	Few sizes are sold of each thing, so every mix of the biggest size and one
	other is tried; that is the whole of the search a customer would do.
	"""
	if amount <= 0 or amount == INF:
		return []
	sizes = sorted(
		(one for one in sold if one.resource == resource and one.size), key=lambda one: one.size, reverse=True
	)
	if not sizes:
		return []
	best, best_price = None, None
	biggest = sizes[0]
	for many in range(int(amount // biggest.size) + 2):
		left = amount - many * biggest.size
		for rest in sizes:
			count = max(0, ceil(left / rest.size)) if left > 0 else 0
			mix = [(biggest, many)] if many else []
			if count:
				mix = [*mix, (rest, count)] if rest is not biggest else [(biggest, many + count)]
			price = sum(one.price * n for one, n in mix)
			if mix and (best_price is None or price < best_price):
				best, best_price = mix, price
	return best or []


def topping(resource: str, amount: float, sold: list[Offer]) -> float | None:
	"""What `amount` more of `resource` costs as add-ons, or None if none is sold."""
	if amount <= 0:
		return 0.0
	if amount == INF:
		return None
	mix = extras_for(resource, amount, sold)
	return round(sum(one.price * n for one, n in mix), 2) if mix else None


def quote(needs: dict, plans: list[Offer], sold: list[Offer]) -> list[Option]:
	"""Every plan that can meet `needs` with add-ons on top, cheapest first.

	`needs` maps a resource to how much of it: seats, storage_gb, database_gb,
	credits_a_month. A plan that cannot be topped up to a need (nothing sold
	of it) says so in `unmet` and goes last.
	"""
	options = []
	for plan in plans:
		option = Option(plan)
		for resource in RESOURCES:
			short = float(needs.get(resource) or 0) - plan.quota(resource)
			if short <= 0:
				continue
			mix = extras_for(resource, short, sold)
			if mix:
				option.extras += mix
			else:
				option.unmet.append(resource)
		options.append(option)
	return sorted(options, key=lambda one: (bool(one.unmet), one.monthly))


def check(plans: list[Offer], sold: list[Offer], costs: Costs) -> list[Finding]:
	"""Everything about the price list that does not make sense."""
	found = []
	ladder = sorted(plans, key=lambda one: one.price)

	# 1. Every price covers what it costs, with the margin.
	for offer in [*ladder, *sold]:
		ours = cost(offer, costs)
		if ours and offer.price < ours * costs.margin:
			found.append(
				Finding(
					"red" if offer.price < ours else "orange",
					offer.key,
					f"{offer.label} sells for {offer.price:g} and costs {ours:.2f} to run, "
					f"under the {costs.margin:g}× margin ({ours * costs.margin:.2f}).",
				)
			)

	# 2. Each plan up gives at least as much of everything, for more.
	for lower, upper in pairwise(ladder):
		for resource in RESOURCES:
			if upper.quota(resource) < lower.quota(resource):
				found.append(
					Finding(
						"red",
						upper.key,
						f"{upper.label} costs more than {lower.label} and gives fewer {NAMED[resource]}.",
					)
				)

	# 3. Moving up is cheaper than buying the difference as add-ons.
	for lower, upper in pairwise(ladder):
		step = upper.price - lower.price
		instead = [topping(one, upper.quota(one) - lower.quota(one), sold) for one in RESOURCES]
		if any(one is None for one in instead):
			continue
		alone = sum(instead)
		if alone and step >= alone:
			found.append(
				Finding(
					"red",
					upper.key,
					f"Moving from {lower.label} to {upper.label} costs {step:g} more a month, and buying the "
					f"difference as add-ons costs {alone:g}, so nobody would move up.",
				)
			)
		elif alone and step > alone * 0.8:
			found.append(
				Finding(
					"orange",
					upper.key,
					f"{upper.label} saves only {100 * (1 - step / alone):.0f}% over {lower.label} with add-ons.",
				)
			)

	# 4. The smallest add-on is cheaper than moving up, or nobody buys it.
	for lower, upper in pairwise(ladder):
		step = upper.price - lower.price
		for resource in RESOURCES:
			smallest = min(
				(one for one in sold if one.resource == resource and one.kind == "Add-on"),
				key=lambda one: one.size,
				default=None,
			)
			if smallest and smallest.price >= step:
				found.append(
					Finding(
						"orange",
						smallest.key,
						f"{smallest.label} costs {smallest.price:g} a month, as much as moving from {lower.label} "
						f"to {upper.label}.",
					)
				)

	# 5. A bigger size of the same thing is no dearer per unit.
	for resource in RESOURCES:
		sizes = sorted(
			(one for one in sold if one.resource == resource and one.size), key=lambda one: one.size
		)
		for small, big in pairwise(sizes):
			if big.price / big.size > small.price / small.size + 1e-9:
				found.append(
					Finding("orange", big.key, f"{big.label} costs more per unit than {small.label}.")
				)
	return found


def upgrade_saving(lower: Offer, upper: Offer, sold: list[Offer]) -> float | None:
	"""How much moving up saves over buying the difference as add-ons, as a
	share: 0.4 is forty per cent. None when a difference cannot be bought."""
	instead = [topping(one, upper.quota(one) - lower.quota(one), sold) for one in RESOURCES]
	if any(one is None for one in instead) or not sum(instead):
		return None
	return 1 - (upper.price - lower.price) / sum(instead)
