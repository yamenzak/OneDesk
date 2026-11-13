"""A signup's setup answers (one/setup_answers.py): those typed into the
wizard (wizard.py), kept on its Account Request, or for a signup made
before the wizard, what OneAdmin keeps of it: the workspace's name, the
owner's address, the country and the time zone on its Tenant and Account
Request."""

import frappe

from onedesk.one import setup_answers

LANGUAGE = "en"


def from_signup(workspace: str, email: str, country: str | None, zone: str | None, zones: dict[str, str]) -> dict | None:
	"""The answers a signup gives: the workspace's name as its company, in
	the country it said or the one its time zone is in, the owner named
	from their address until the wizard asks. None when no country can be
	told, and the owner meets frappe's wizard on their site instead. Pure."""
	country = country or zones.get(zone or "")
	if not (workspace and email and country and zone):
		return None
	return setup_answers.check(
		{
			"owner": {"email": email, "first_name": email.split("@", 1)[0]},
			"language": LANGUAGE,
			"time_zone": zone,
			"companies": [{"name": workspace, "country": country}],
		}
	)


def zones() -> dict[str, str]:
	"""The country each time zone is in, where it is in one only, from
	frappe's country list."""
	from frappe.geo.country_info import get_all

	found: dict[str, set] = {}
	for country, info in get_all().items():
		for zone in info.get("timezones") or []:
			found.setdefault(zone, set()).add(country)
	return {zone: next(iter(countries)) for zone, countries in found.items() if len(countries) == 1}


def from_wizard(said: dict, email: str) -> dict | None:
	"""The wizard's answers with the owner's address the workspace's own,
	whoever typed it; None while they can't be set up from. Pure."""
	if not said:
		return None
	said = {**said, "owner": {**(said.get("owner") or {}), "email": email}}
	try:
		return setup_answers.check(said)
	except setup_answers.Invalid:
		return None


def of(tenant) -> dict | None:
	"""The answers OneAdmin holds for a tenant's signup."""
	asked = frappe.db.get_value("Account Request", {"tenant": tenant.name}, ["country", "time_zone", "answers"], as_dict=True, order_by="creation desc") or {}
	email = (tenant.owner_email or "").strip().lower()
	wizard = from_wizard(frappe.parse_json(asked.get("answers") or "{}") or {}, email)
	if wizard:
		return wizard
	return from_signup(
		tenant.workspace_name,
		email,
		tenant.country or asked.get("country"),
		tenant.time_zone or asked.get("time_zone"),
		zones(),
	)


ANSWERING_MINUTES = 30


def answering(tenant) -> bool:
	"""Whether the owner is still answering the wizard's steps after
	payment (wizard.py): steps.set_up waits for them, for at most
	ANSWERING_MINUTES after payment, then sets up from what is there."""
	from frappe.utils import now_datetime, time_diff_in_seconds

	asked = frappe.db.get_value("Account Request", {"tenant": tenant.name}, ["answers", "answered_on"], as_dict=True, order_by="creation desc")
	if not asked or not asked.answers or asked.answered_on:
		return False
	return time_diff_in_seconds(now_datetime(), tenant.creation) < ANSWERING_MINUTES * 60
