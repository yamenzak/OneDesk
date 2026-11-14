"""What the setup wizard offers (one_admin/wizard.py): the fields and the
apps each starts with, every app with what it needs and why one is kept,
the countries with their currency and time zones, the languages One is
written in, the plans with what they include, where data may be kept, and
each app's own steps. Read only."""

from base64 import b64encode
from pathlib import Path

import frappe
from frappe import _

from onedesk.one import registry
from onedesk.one.registry import features, fields, switches

LOCALE = Path(__file__).resolve().parents[1] / "locale"
BRAND = Path(__file__).resolve().parents[2] / "brand"

WHERE = {"Global": "Global", "EU": "European Union"}

WEEKEND = {"Saudi Arabia": ("Friday", "Saturday"), "Qatar": ("Friday", "Saturday"), "Kuwait": ("Friday", "Saturday"), "Bahrain": ("Friday", "Saturday"), "Oman": ("Friday", "Saturday"), "Egypt": ("Friday", "Saturday"), "Jordan": ("Friday", "Saturday"), "Iran": ("Friday",), "Afghanistan": ("Friday",)}
"""The days off a working week starts with where they are not Saturday and Sunday."""
WEEKEND_ELSEWHERE = ("Saturday", "Sunday")
DAY = ("09:00", "17:00")


def offer() -> dict:
	"""Everything the wizard asks from, in the reader's language."""
	sold = plans()
	return {
		"fields": [{"id": one.id, "label": _(one.label), "line": _(one.line), "apps": list(fields.preset(one.id))} for one in fields.FIELDS],
		"apps": apps(),
		"countries": countries(),
		"languages": languages(),
		"plans": sold,
		"regions": regions(),
		"weekend": {country: list(days) for country, days in WEEKEND.items()},
		"weekend_elsewhere": list(WEEKEND_ELSEWHERE),
		"day": list(DAY),
		"domain": frappe.db.get_single_value("One Admin Settings", "tenant_domain") or "t.4dl.app",
		"me": frappe.db.get_value("User", frappe.session.user, "email") if frappe.session.user != "Guest" else None,
		"pay_note": pay_note(sold),
	}


def days_off(country: str | None) -> list[str]:
	"""The days off a working week starts with in this country."""
	return list(WEEKEND.get(country, WEEKEND_ELSEWHERE))


def _mark(id: str) -> str | None:
	path = BRAND / f"{id}.svg"
	if not id or not path.is_file():
		return None
	return "data:image/svg+xml;base64," + b64encode(path.read_bytes()).decode()


def apps() -> list[dict]:
	"""Each app a workspace may turn on, and each always on with why."""
	kept = {one.id for one in switches.always()}
	return [
		{
			"id": one.id,
			"name": one.name,
			"line": _(one.line) if one.line else "",
			"mark": _mark(one.mark),
			"needs": list(one.needs),
			"always": one.id in kept,
			"kept": _(one.kept.why) if one.kept else None,
		}
		for one in (*switches.always(), *switches.switches())
	]


def countries() -> list[dict]:
	"""Every country frappe knows, its currency and time zones, by its name
	in the reader's language."""
	from frappe.geo.country_info import get_all

	found = [
		{"value": name, "label": _(name), "currency": info.get("currency"), "zones": info.get("timezones") or []}
		for name, info in get_all().items()
	]
	return sorted(found, key=lambda one: one["label"])


def languages() -> list[dict]:
	"""English and every language One is translated into."""
	codes = ["en", *sorted(path.stem for path in LOCALE.glob("*.po") if path.stem != "en")]
	names = dict(frappe.get_all("Language", filters={"name": ["in", codes]}, fields=["name", "language_name"], as_list=True))
	return [{"value": code, "label": names.get(code) or code} for code in codes]


def regions() -> list[dict]:
	"""Where a workspace may be kept, and only where there is somewhere to
	keep it: the EU moves its files to the EU bucket (storage._bucket), so
	it is offered once that bucket is set."""
	eu = frappe.db.get_single_value("One Admin Settings", "bucket_eu")
	return [{"value": key, "label": _(label)} for key, label in WHERE.items() if key != "EU" or eu]


def plans() -> list[dict]:
	"""The plans on offer, cheapest first, with their price, trial, quotas
	and what each includes."""
	from onedesk.one_admin import features as held

	rows = frappe.get_all(
		"Offering",
		filters={"kind": "Plan", "enabled": 1},
		fields=["name", "label", "description", "currency", "amount", "trial_days", "storage_gb", "database_gb", "seats", "credits_a_month"],
		order_by="amount asc",
	)
	for one in rows:
		one["price"] = _("{0} a month").format(frappe.utils.fmt_money(one["amount"], currency=one["currency"]))
		one["trial"] = _("Free for {0} days").format(one["trial_days"]) if one.get("trial_days") else None
		one["quota"] = " · ".join(quota(one))
		one["includes"] = [_(features.get(id).label) for id in held.held("Offering", one["name"]) if id in features.IDS]
	return rows


def quota(one: dict) -> list[str]:
	"""What the plan buys, in the order somebody compares plans in. A zero
	is unlimited, and saying so on a signup page is a promise, so it is left
	out."""
	said = []
	if one.get("storage_gb"):
		said.append(_("{0} GB storage").format(_count(one["storage_gb"])))
	if one.get("database_gb"):
		said.append(_("{0} GB database").format(_count(one["database_gb"])))
	if one.get("seats"):
		said.append(_("{0} people").format(_count(one["seats"])))
	if one.get("credits_a_month"):
		said.append(_("{0} credits a month").format(_count(one["credits_a_month"])))
	return said


def _count(value) -> str:
	"""A whole number as the workspace writes numbers."""
	return frappe.utils.fmt_money(value, precision=0)


def pay_note(offerings: list[dict]) -> str:
	"""The line under Pay, true of whatever is picked: a plan with a trial
	takes the card now and charges it later."""
	if any(one.get("trial_days") for one in offerings):
		return _("Payment is taken by Stripe. A plan with a trial takes your card now and charges it when the trial ends.")
	return _("Payment is taken by Stripe. Nothing is charged until it is confirmed there.")


def on(answers: dict) -> list[str]:
	"""The apps these answers have on: those always on, then those the
	answers turn on, or a field's preset while they say none."""
	said = answers.get("apps")
	chosen = [id for id, yes in said.items() if yes] if said else list(fields.preset(answers.get("field")))
	return [*(one.id for one in switches.always()), *switches.with_needs(chosen)]


def steps(answers: dict) -> list[dict]:
	"""Each app's own steps that ask something, for the apps on, in the
	rail's order (one/setup_steps.py): a screen each after payment."""
	from onedesk.one import ready, setup_steps

	turned = set(on(answers))
	order = {one.id: at for at, one in enumerate(registry.apps())}
	found = []
	for module, step in setup_steps.declared():
		folder = ready.MODULES[module]["folder"]
		if not step.get("fields") or folder not in turned:
			continue
		found.append(
			{
				"id": f"steps:{folder}.{step['key']}",
				"app": folder,
				"key": step["key"],
				"app_name": registry.name(folder),
				"title": said(step.get("title")),
				"about": said(step.get("about")),
				"fields": [_field(one) for one in step["fields"]],
			}
		)
	return sorted(found, key=lambda one: order.get(one["app"], len(order)))


def said(text) -> str:
	"""A step's own words in the reader's language, as a string a response
	can carry (a step declares them with _lt); nothing for none."""
	return str(_(text)) if text else ""


def _field(given: dict) -> dict:
	return {
		"fieldname": given["fieldname"],
		"fieldtype": given.get("fieldtype") or "Data",
		"label": said(given.get("label")),
		"description": said(given.get("description")),
		"options": [one for one in str(given.get("options") or "").split("\n") if one],
		"default": given.get("default"),
	}


def seats(offering: str | None) -> int:
	"""The people a plan holds, the owner among them; 0 for no limit."""
	return int(frappe.db.get_value("Offering", offering, "seats") or 0) if offering else 0

