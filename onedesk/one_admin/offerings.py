"""The price list a new admin site starts with, and what it costs us.

Four plans from 30 a month, the add-ons that go on them, and the credit
packs. Written once: `install` adds what is missing by key and never touches
an offering that exists, because the operator's prices are theirs to change
and a migrate must not put the old ones back. The Price Check report says
whether the list still makes sense after they do (plans.py).

Why these numbers, briefly (the Price Check shows the rest):

* Each plan is at least twice what it costs us (`COSTS`), and each step up
  saves more than half over buying the difference as add-ons, so somebody
  who has outgrown a plan is better off moving up.
* The smallest add-on of each thing costs less than any step up, so
  somebody who needs a little more is better off adding it.
* A bigger add-on is cheaper per unit than a smaller one.
* Database is dear and storage is cheap, because a GB of database moves the
  site up Frappe Cloud's plans and is backed up every day, where a GB of
  files is a GB in R2.
"""

import frappe
from frappe.utils import flt

from onedesk.one_admin import plans, site

#: What a month of each thing costs us, in US dollars. Estimates to start
#: from: the operator sets the real ones in One Admin Settings, Costs.
COSTS = {
	"cost_workspace": 8,  # the smallest Frappe Cloud site, and its mail
	"cost_seat": 0.5,
	"cost_storage_gb": 0.02,  # R2 at 0.015, and its operations
	"cost_database_gb": 3,  # what a GB adds to the site's Frappe Cloud plan
	"cost_backup_gb": 0.015,  # a backup copy in R2
	"backups_kept": 14,
	"least_margin": 2,
}

PLANS = [
	# key, label, price, seats, storage GB, database GB, credits a month, trial days
	("starter", "Starter", 30, 5, 20, 1, 1000, 14),
	("team", "Team", 70, 15, 100, 3, 3000, 14),
	("business", "Business", 150, 40, 300, 8, 8000, 0),
	("scale", "Scale", 300, 100, 1000, 15, 20000, 0),
]

ADDONS = [
	# key, label, price, what it adds
	("storage-50", "50 GB of Storage", 5, {"storage_gb": 50}),
	("storage-250", "250 GB of Storage", 20, {"storage_gb": 250}),
	("database-1", "1 GB of Database", 9, {"database_gb": 1}),
	("database-5", "5 GB of Database", 40, {"database_gb": 5}),
	("seats-5", "5 Seats", 20, {"seats": 5}),
]

PACKS = [
	# key, label, price, credits
	("pack1k", "1,000 credits", 9, 1000),
	("pack5k", "5,000 credits", 40, 5000),
	("pack20k", "20,000 credits", 150, 20000),
]

CURRENCY = "USD"


def rows() -> list[dict]:
	"""Every offering above, as the Offering it becomes."""
	made = [
		{
			"key": key,
			"label": label,
			"kind": "Plan",
			"amount": price,
			"recurring": 1,
			"trial_days": trial,
			"seats": seats,
			"storage_gb": storage,
			"database_gb": database,
			"credits_a_month": credits,
		}
		for key, label, price, seats, storage, database, credits, trial in PLANS
	]
	made += [
		{"key": key, "label": label, "kind": "Add-on", "amount": price, "recurring": 1, **adds}
		for key, label, price, adds in ADDONS
	]
	made += [
		{
			"key": key,
			"label": label,
			"kind": "Credit Pack",
			"amount": price,
			"recurring": 0,
			"credits": credits,
		}
		for key, label, price, credits in PACKS
	]
	return [{"doctype": "Offering", "currency": CURRENCY, "enabled": 1, **one} for one in made]


def install(*_args) -> None:
	"""Add what is missing, on the admin site only; change nothing that exists."""
	if not site.is_admin() or not frappe.db.table_exists("Offering"):
		return
	for one in rows():
		if not frappe.db.exists("Offering", one["key"]):
			frappe.get_doc(one).insert(ignore_permissions=True)
	settings = frappe.get_single("One Admin Settings")
	unset = {field: value for field, value in COSTS.items() if not settings.get(field)}
	if unset:
		settings.db_set(unset)


def listed(including_off: bool = False) -> tuple[list, list, "plans.Costs"]:
	"""The price list and what it costs us, as plans.py reads them: the plans,
	everything sold on top of one (add-ons and packs), and the costs."""
	filters = {} if including_off else {"enabled": 1}
	held = frappe.get_all(
		"Offering",
		filters=filters,
		fields=[
			"key",
			"label",
			"kind",
			"amount",
			"seats",
			"storage_gb",
			"database_gb",
			"credits_a_month",
			"credits",
		],
		order_by="amount asc",
	)
	made = [
		plans.Offer(
			key=one.key,
			label=one.label,
			kind=one.kind,
			price=flt(one.amount),
			seats=one.seats or 0,
			storage_gb=one.storage_gb or 0,
			database_gb=one.database_gb or 0,
			credits_a_month=one.credits_a_month or 0,
			credits=one.credits or 0,
		)
		for one in held
	]
	return [one for one in made if one.kind == "Plan"], [one for one in made if one.kind != "Plan"], costs()


def costs() -> "plans.Costs":
	"""What each thing costs us a month (One Admin Settings, Costs).
	A credit costs what a dollar of provider cost buys, marked up: the
	gateway prices a call the same way (ai_model.py)."""
	held = frappe.get_single("One Admin Settings")
	per_dollar = flt(held.credits_per_dollar) * (flt(held.default_markup) or 1)
	return plans.Costs(
		workspace=flt(held.cost_workspace),
		seat=flt(held.cost_seat),
		storage_gb=flt(held.cost_storage_gb),
		database_gb=flt(held.cost_database_gb),
		backup_gb=flt(held.cost_backup_gb),
		backups_kept=int(held.backups_kept or 0),
		credit=1 / per_dollar if per_dollar else 0,
		margin=flt(held.least_margin) or 2,
	)


def currency() -> str:
	"""What the price list is in: the plans', which every offering shares."""
	return frappe.db.get_value("Offering", {"kind": "Plan", "enabled": 1}, "currency") or CURRENCY
