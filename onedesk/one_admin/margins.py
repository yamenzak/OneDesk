"""Whether what One sells makes money: every plan, add-on and pack priced
against what it costs us at its worst (every seat working, storage and
database full, every credit it gives spent, an international card paid in
euros), and the ladder checked so nobody is better off staying on a smaller
plan (plans.check). Anything under `price_list.MARGIN_FLOOR` is a finding,
and the price list's test refuses it. Pure."""

from dataclasses import dataclass, field

from onedesk.one_admin import price_list, costs, plans


@dataclass
class Priced:
	key: str
	label: str
	price: float
	fee: float
	lines: dict = field(default_factory=dict)

	@property
	def cost(self) -> float:
		return round(sum(self.lines.values()), 2)

	@property
	def margin(self) -> float:
		"""What is left of the price after Stripe and our costs, as a share."""
		return round((self.price - self.fee - self.cost) / self.price, 4) if self.price else 0.0


def credit_cost(credits: float) -> float:
	"""What `credits` credits cost us when all are spent, at the lowest
	markup any kind of usage carries. Pure."""
	return credits * price_list.ONECREDIT / min(price_list.MARKUP.values())


def _resources(seats=0, storage_gb=0, database_gb=0) -> dict:
	return {
		"seats": seats * costs.COST["server_seat"],
		"storage": storage_gb * costs.COST["storage_gb"],
		"database": database_gb * costs.COST["database_gb"],
	}


def fits(one: price_list.Plan) -> bool:
	"""Whether a plan's workspace, full, takes no more than its share of a
	shared server. Pure."""
	return one.seats <= costs.SEATS_A_SERVER * costs.SHARE_MOST and one.database_gb <= costs.SERVER["disk_gb"] * costs.SHARE_MOST


def plan(one: price_list.Plan) -> Priced:
	if one.own_server:
		backups = one.database_gb * costs.R2_GB_MONTH * costs.BACKUP_COMPRESSION * costs.BACKUPS_KEPT
		lines = {
			"server": costs.OWN_SERVER["aed_a_month"],
			"cloudflare": costs.COST["cloudflare_fixed"],
			"storage": one.storage_gb * costs.COST["storage_gb"],
			"database": backups,
			"credits": credit_cost(one.credits_a_month),
		}
	else:
		lines = {
			"workspace": costs.COST["server_workspace"],
			"cloudflare": costs.COST["cloudflare_fixed"],
			**_resources(one.seats, one.storage_gb, one.database_gb),
			"credits": credit_cost(one.credits_a_month),
		}
	return Priced(one.key, one.label, one.price, costs.stripe_fee(one.price), {k: round(v, 4) for k, v in lines.items()})


def addon(one: price_list.AddOn) -> Priced:
	lines = _resources(**{key: value for key, value in one.gives.items() if key in ("seats", "storage_gb", "database_gb")})
	return Priced(one.key, one.label, one.price, costs.stripe_fee(one.price), {k: round(v, 4) for k, v in lines.items() if v})


def pack(one: price_list.Pack) -> Priced:
	return Priced(one.key, one.label, one.price, costs.stripe_fee(one.price), {"credits": round(credit_cost(one.credits), 4)})


def usage(kind: str) -> float:
	"""What is left of a OneCredit spent on `kind`, bought in the smallest
	pack at the worst fee, as a share. Pure."""
	smallest = min(price_list.PACKS, key=lambda one: one.price)
	paid = (smallest.price - costs.stripe_fee(smallest.price)) / smallest.credits
	return round(1 - (price_list.ONECREDIT / price_list.MARKUP[kind]) / paid, 4)


def priced() -> list[Priced]:
	"""Everything sold, priced. Pure."""
	sold_plans, sold_addons, sold_packs = price_list.selling()
	return [*map(plan, sold_plans), *map(addon, sold_addons), *map(pack, sold_packs)]


def _offer(one) -> plans.Offer:
	if isinstance(one, price_list.Plan):
		return plans.Offer(one.key, one.label, "Plan", one.price, one.seats, one.storage_gb, one.database_gb, one.credits_a_month)
	if isinstance(one, price_list.AddOn):
		return plans.Offer(one.key, one.label, "Add-on", one.price, **one.gives)
	return plans.Offer(one.key, one.label, "Credit Pack", one.price, credits=one.credits)


def findings(floor: float = price_list.MARGIN_FLOOR) -> list[plans.Finding]:
	"""Everything that loses money or makes no sense on the ladder. Pure."""
	found = [
		plans.Finding(
			"red",
			one.key,
			f"{one.label} keeps {one.margin:.0%} of its {price_list.CURRENCY} {one.price:g} at worst, under the {floor:.0%} floor.",
			"margin",
		)
		for one in priced()
		if one.margin < floor
	]
	for one in price_list.selling()[0]:
		if not one.own_server and not fits(one):
			found.append(plans.Finding("red", one.key, f"{one.label} takes more than {costs.SHARE_MOST:.0%} of a shared server when full; give it its own.", "fits"))
		if one.own_server and one.database_gb > costs.OWN_SERVER["disk_gb"] * 0.5:
			found.append(plans.Finding("red", one.key, f"{one.label}'s database would fill half its own server's disk.", "fits"))
	for kind in price_list.MARKUP:
		if usage(kind) < floor:
			found.append(plans.Finding("red", kind, f"A OneCredit spent on {kind} keeps {usage(kind):.0%}, under the {floor:.0%} floor.", "usage"))
	sold_plans, sold_addons, sold_packs = price_list.selling()
	ladder = [found for found in plans.check([*map(_offer, sold_plans)], [*map(_offer, (*sold_addons, *sold_packs))], plans.Costs()) if found.rule != "margin"]
	return found + ladder


def table() -> str:
	"""Every price and what is left of it, for a person to read. Pure."""
	rows = [f"{'':<22}{'price':>9}{'stripe':>9}{'cost':>9}{'margin':>9}"]
	for one in priced():
		rows.append(f"{one.label:<22}{one.price:>9.2f}{one.fee:>9.2f}{one.cost:>9.2f}{one.margin:>9.0%}")
	rows.append("")
	rows += [f"a OneCredit on {kind:<11}keeps {usage(kind):.0%}" for kind in price_list.MARKUP]
	rows.append("")
	rows += [f"{line.key:<20}{price_list.CURRENCY} {line.amount:>8.4f} a {line.per}{'' if line.measured else '  (estimate)'}" for line in costs.LINES]
	said = findings()
	rows.append("")
	rows += [f"{one.level.upper():<7}{one.said}" for one in said] or ["Nothing loses money or makes no sense."]
	return "\n".join(rows)
