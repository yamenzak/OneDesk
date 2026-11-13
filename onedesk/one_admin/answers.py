"""A signup's setup answers (one/setup_answers.py), from what OneAdmin
keeps of it: the workspace's name, the owner's address, the country and
the time zone on its Tenant and Account Request. The wizard's own answers
join these on the Account Request (docs/run/RUN.md P4.4)."""

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


def of(tenant) -> dict | None:
	"""The answers OneAdmin holds for a tenant's signup."""
	asked = frappe.db.get_value("Account Request", {"tenant": tenant.name}, ["country", "time_zone"], as_dict=True, order_by="creation desc") or {}
	return from_signup(
		tenant.workspace_name,
		(tenant.owner_email or "").strip().lower(),
		tenant.country or asked.get("country"),
		tenant.time_zone or asked.get("time_zone"),
		zones(),
	)
