"""What One sells, declared here and nowhere else: plans, add-ons, OneCredit
packs and services, each versioned in its key (`team@2026-12`), what a
OneCredit is worth, the trial and tax. A version is never edited; a change
is a new one. Offering rows are written from it (offerings.py) and
margins.py refuses what would lose money (README, Under the hood, The price
list). Pure."""

from dataclasses import dataclass, field

CURRENCY = "AED"
EUR_PER_AED = 0.235

ONECREDIT = 0.04
MARGIN_FLOOR = 0.40

YEARLY_MONTHS = 10


@dataclass(frozen=True)
class Plan:
	key: str
	label: str
	price: float
	seats: int
	storage_gb: float
	database_gb: float
	credits_a_month: int
	own_server: bool = False
	sold: bool = True


@dataclass(frozen=True)
class AddOn:
	key: str
	label: str
	price: float
	gives: dict = field(default_factory=dict)
	sold: bool = True


@dataclass(frozen=True)
class Pack:
	key: str
	label: str
	price: float
	credits: int
	sold: bool = True


@dataclass(frozen=True)
class Service:
	key: str
	label: str
	price: float
	does: str


PLANS = (
	Plan("starter@2026-12", "Starter", 109, 5, 50, 2, 500),
	Plan("team@2026-12", "Team", 299, 15, 200, 5, 1500),
	Plan("business@2026-12", "Business", 749, 40, 500, 15, 4000, own_server=True),
	Plan("scale@2026-12", "Scale", 1699, 100, 1500, 40, 10000, own_server=True),
)

ADDONS = (
	AddOn("seats-5@2026-12", "5 Seats", 89, {"seats": 5}),
	AddOn("storage-100@2026-12", "100 GB of Storage", 29, {"storage_gb": 100}),
	AddOn("storage-500@2026-12", "500 GB of Storage", 119, {"storage_gb": 500}),
	AddOn("database-2@2026-12", "2 GB of Database", 29, {"database_gb": 2}),
	AddOn("database-10@2026-12", "10 GB of Database", 119, {"database_gb": 10}),
)

PACKS = (
	Pack("credits-1k@2026-12", "1,000 OneCredits", 45, 1000),
	Pack("credits-5k@2026-12", "5,000 OneCredits", 199, 5000),
	Pack("credits-20k@2026-12", "20,000 OneCredits", 749, 20000),
)

SERVICES = (
	Service("one-setup", "One Setup", 9999, "Your workspace set up with you: company, accounts, data moved from your old system, and your people shown how."),
)

MARKUP = {"ai": 2.0, "oneos": 2.0, "office": 2.0, "mail": 2.0}

MAIL_CREDITS = 1

TRIAL = {"days": 14, "card": False, "credits": 500, "dropped_after_days": 14}

TAX = {"registered": False, "rate": 0.05, "inclusive": False}

PACK_CREDITS_LAST_DAYS = 365


def credits_per_dollar() -> float:
	"""How many OneCredits a dollar of our cost is before markup: a dollar in
	dirhams over a OneCredit's value. Pure."""
	from onedesk.one_admin.costs import AED_PER_USD

	return round(AED_PER_USD / ONECREDIT, 4)


def selling() -> tuple[tuple, tuple, tuple]:
	"""The plans, add-ons and packs new signups may buy. Pure."""
	return tuple(one for one in PLANS if one.sold), tuple(one for one in ADDONS if one.sold), tuple(one for one in PACKS if one.sold)


def yearly(price: float) -> float:
	"""A plan's price paid for a year: `YEARLY_MONTHS` months. Pure."""
	return round(price * YEARLY_MONTHS, 2)


def family(key: str) -> str:
	"""A versioned key without its version: `team@2026-12` is `team`. Pure."""
	return key.split("@", 1)[0]
