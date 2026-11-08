"""What running One costs us, line by line, in the price list's currency,
declared here and only here. margins.py prices everything sold against it;
each line says whether it was measured or is still an estimate (README,
Under the hood, What One costs us). Pure."""

from dataclasses import dataclass

AED_PER_USD = 3.6725


def usd(amount: float) -> float:
	"""Dollars as dirhams. Pure."""
	return round(amount * AED_PER_USD, 6)


@dataclass(frozen=True)
class Line:
	"""One cost: what it is, its amount in AED, what it is per, where the
	figure comes from, and whether it was measured."""

	key: str
	amount: float
	per: str
	source: str
	measured: bool = False


SERVER = {"aed_a_month": usd(40), "disk_gb": 80}
OWN_SERVER = {"aed_a_month": usd(70), "disk_gb": 160}
SHARE_MOST = 0.25
WORKSPACES_A_SERVER = 20
SEATS_A_SERVER = 200

CLOUDFLARE_FIXED = {"workers_paid": usd(5), "advanced_certificate_manager": usd(10)}
TENANTS_SHARING = 20

R2_GB_MONTH = usd(0.015)
FILE_COPIES = 2
BACKUP_COMPRESSION = 0.25
BACKUPS_KEPT = 42

STRIPE_SHARE = 0.029
STRIPE_FIXED = 1.0
STRIPE_INTERNATIONAL = 0.01
STRIPE_CONVERSION = 0.01
STRIPE_BILLING = 0.007


def stripe_fee(amount: float, worst: bool = True) -> float:
	"""What Stripe keeps of a payment in AED: at worst an international card
	paid in euros. Pure."""
	share = STRIPE_SHARE + STRIPE_BILLING + ((STRIPE_INTERNATIONAL + STRIPE_CONVERSION) if worst else 0)
	return round(amount * share + STRIPE_FIXED, 4) if amount else 0.0


LINES = (
	Line("server_workspace", SERVER["aed_a_month"] / 2 / WORKSPACES_A_SERVER, "workspace a month", "half the server over the workspaces it holds; an estimate until measured"),
	Line("server_seat", SERVER["aed_a_month"] / 2 / SEATS_A_SERVER, "seat a month", "half the server over the seats it holds; an estimate until measured"),
	Line("database_gb", SERVER["aed_a_month"] / SERVER["disk_gb"] * 2 + R2_GB_MONTH * BACKUP_COMPRESSION * BACKUPS_KEPT, "GB of database a month", "the server's disk twice over, for the memory a database also takes, and its backups in R2"),
	Line("storage_gb", R2_GB_MONTH * FILE_COPIES, "GB of files a month", "R2, the file and its backup copy"),
	Line("cloudflare_fixed", sum(CLOUDFLARE_FIXED.values()) / TENANTS_SHARING, "workspace a month", "Workers Paid and Advanced Certificate Manager over the workspaces sharing them"),
)

COST = {one.key: one.amount for one in LINES}
