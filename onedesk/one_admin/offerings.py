"""The price list as OneAdmin's Offering rows, written from the code
(price_list.py) on every migrate and never edited by hand. A row whose key
the price list no longer sells is turned off for new signups and kept, so a
workspace on that version keeps paying its Stripe price (grandfathering).
"""

import frappe
from frappe import _, _lt
from frappe.utils import flt

from onedesk.one import registry
from onedesk.one_admin import costs as ours
from onedesk.one_admin import features, plans, price_list, site

SYNCING = "one_admin_price_list_sync"


def _row(one) -> dict:
	sold = one in (*price_list.selling()[0], *price_list.selling()[1], *price_list.selling()[2])
	if isinstance(one, price_list.Plan):
		made = {
			"kind": "Plan",
			"recurring": 1,
			"trial_days": 0,
			"seats": one.seats,
			"storage_gb": one.storage_gb,
			"database_gb": one.database_gb,
			"credits_a_month": one.credits_a_month,
			"features": features.rows(one.features),
		}
	elif isinstance(one, price_list.AddOn):
		made = {"kind": "Add-on", "recurring": 1, **one.gives}
	else:
		made = {"kind": "Credit Pack", "recurring": 0, "credits": one.credits}
	return {"doctype": "Offering", "key": one.key, "label": one.label, "amount": one.price, "currency": price_list.CURRENCY, "enabled": int(sold), **made}


def rows() -> list[dict]:
	"""Every plan, add-on and pack the price list declares, as its Offering."""
	return [_row(one) for one in (*price_list.PLANS, *price_list.ADDONS, *price_list.PACKS)]


def install(*_args) -> None:
	"""After migrate, on the admin site: each declared offering made if it is
	not there, sold or not as the price list says, and every other one off. A
	declared row's price is never changed: a new price is a new version. Its
	features are the price list's: a Tenant keeps the copy it bought."""
	if not site.is_admin() or not frappe.db.table_exists("Offering"):
		return
	frappe.flags[SYNCING] = True
	try:
		declared = {}
		for one in rows():
			declared[one["key"]] = one["enabled"]
			if not frappe.db.exists("Offering", one["key"]):
				frappe.get_doc(one).insert(ignore_permissions=True)
			elif one["kind"] == "Plan":
				features.write("Offering", one["key"], [row["feature"] for row in one["features"]])
		for key, enabled in frappe.get_all("Offering", fields=["name", "enabled"], as_list=True):
			want = declared.get(key, 0)
			if int(enabled or 0) != want:
				frappe.db.set_value("Offering", key, "enabled", want, update_modified=False)
	finally:
		frappe.flags[SYNCING] = False


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
	"""What each thing costs us a month, from costs.py, as plans.py reads
	them; the margin is the price list's floor as a multiple of cost."""
	return plans.Costs(
		workspace=ours.COST["server_workspace"] + ours.COST["cloudflare_fixed"],
		seat=ours.COST["server_seat"],
		storage_gb=ours.COST["storage_gb"],
		database_gb=ours.COST["database_gb"],
		credit=price_list.ONECREDIT / min(price_list.MARKUP.values()),
		margin=round(1 / (1 - price_list.MARGIN_FLOOR), 4),
	)


@frappe.whitelist()
@frappe.read_only()
def rates() -> list[dict]:
	"""What is charged in OneCredits for what a workspace uses rather than
	buys, from the code beside each: a conversion, a mail, a minute of OneOS
	at each instance type."""
	site.require_admin()
	frappe.has_permission("Offering", "read", throw=True)
	from onedesk.one_admin import office, oneos

	made = [
		{"what": _("Office file to PDF"), "per": _("Conversion, at least"), "credits": office.LEAST},
		{"what": _("Mail from {0}").format(registry.name("one_mail")), "per": _("Mail"), "credits": price_list.MAIL_CREDITS},
	]
	return made + [
		{"what": _("OneOS, {0}").format(one["size"]), "per": _("Minute"), "credits": one["credits_a_minute"]}
		for one in oneos.rates()
	]


def currency() -> str:
	"""What the price list is in: the plans', which every offering shares."""
	return frappe.db.get_value("Offering", {"kind": "Plan", "enabled": 1}, "currency") or price_list.CURRENCY


def credit_price() -> float:
	"""What one credit sells for: the smallest enabled credit pack's price over
	its credits, the list price before any bigger pack's discount. Not
	Credits per Dollar, which is what a dollar of provider cost becomes."""
	pack = frappe.get_all(
		"Offering",
		filters={"kind": "Credit Pack", "enabled": 1, "credits": [">", 0]},
		fields=["amount", "credits"],
		order_by="credits asc",
		limit=1,
	)
	return flt(pack[0].amount) / flt(pack[0].credits) if pack else 0.0


RULES = {
	"margin": _lt("{label} sells for {price} and costs {cost}, below the {margin}× margin ({least})."),
	"fewer": _lt("{upper} costs more than {lower} and gives less {what}."),
	"no_upgrade": _lt(
		"Moving from {lower} to {upper} costs {step} more a month, but the same as add-ons costs {alone}."
	),
	"thin_upgrade": _lt("{upper} saves only {saves}% over {lower} with add-ons."),
	"addon_dear": _lt("{addon} costs {price} a month, as much as moving from {lower} to {upper}."),
	"per_unit": _lt("{big} costs more per unit than {small}."),
}

RESOURCE_SAID = {
	"seats": _lt("seats"),
	"storage_gb": _lt("storage"),
	"database_gb": _lt("database"),
	"credits_a_month": _lt("credits a month"),
}


def said(finding) -> str:
	"""One finding in the reader's language."""
	words = RULES.get(finding.rule)
	if not words or not finding.slots:
		return finding.said
	slots = dict(finding.slots)
	if "resource" in slots:
		slots["what"] = str(RESOURCE_SAID.get(slots["resource"], slots["resource"]))
	return str(words).format(**slots)


def findings(offer: str | None = None) -> list[dict]:
	"""What the calculator finds about what is sold (margins.py), in words,
	the wrong first: all of it, or only what is about one offering."""
	from onedesk.one_admin import margins

	found = margins.findings()
	if offer:
		found = [one for one in found if one.offer == offer]
	found.sort(key=lambda one: one.level != "red")
	return [{"level": one.level, "offering": one.offer, "said": said(one)} for one in found]


def warn(doc, method=None) -> None:
	"""Offering and One Admin Settings on_update: say at once what the price
	list now gets wrong, rather than leaving it for Price Check to find. An
	offering says what is about it; the costs say everything."""
	if not site.is_admin() or frappe.flags.in_install or frappe.flags.in_migrate or frappe.flags.in_patch:
		return
	if doc.doctype == "Offering" and not doc.enabled:
		return
	found = findings(doc.name if doc.doctype == "Offering" else None)
	if not found:
		return
	frappe.msgprint(
		"<br>".join(frappe.utils.escape_html(one["said"]) for one in found),
		title=frappe._("Price List Problems"),
		indicator="red" if any(one["level"] == "red" for one in found) else "orange",
	)
