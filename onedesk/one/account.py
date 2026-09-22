"""Asking the administrator, from a workspace that holds one secret.

A tenant site knows four things, all written into its own config when it was
provisioned: where admin is, which workspace it is, the token that proves it, and
what hostname it answers on. It knows no provider key, no bucket credential and
no press token, and that is the whole security argument — a workspace that is
compromised gives up itself and nothing else.

**Nothing here decides anything.** Quota, price and permission are admin's
answers; this asks and records. A tenant site that could decide its own quota is
a tenant site that could raise it.

**An outage degrades rather than stops.** `refresh` failing leaves the last
answer in place with the error beside it, so a header keeps drawing what was
last true. What does not survive is anything that needs a fresh decision — a new
upload, an AI call — and that is the right thing to be fragile about.
"""

import frappe
import requests
from frappe.utils import now_datetime

from onedesk.one_admin import faults, proxy

#: How long to wait on admin. A workspace drawing a page should not be held up
#: by somebody else's slow request, and every one of these calls has a cached
#: answer to fall back on.
PATIENCE = 10

#: The config keys `steps.push_config` writes. Named here so a site missing one
#: says which rather than failing at a request.
NEEDED = ("one_admin_url", "one_tenant", "one_token")


def configured() -> bool:
	return all(frappe.conf.get(key) for key in NEEDED)


def ask(endpoint: str, **params):
	"""Call one admin endpoint and return its answer.

	The slug goes in the body because admin rate-limits on it; the token goes in
	a header of ours, because a token in a body is a token in a traceback and
	`Authorization` is one Frappe reads for itself.
	"""
	if not configured():
		missing = [key for key in NEEDED if not frappe.conf.get(key)]
		raise faults.Refused(f"This workspace is not linked to an account: {', '.join(missing)}")

	url = f"{frappe.conf.get('one_admin_url').rstrip('/')}/api/method/{endpoint}"
	try:
		answer = requests.post(
			url,
			headers={proxy.HEADER: frappe.conf.get("one_token")},
			json={"tenant": frappe.conf.get("one_tenant"), **params},
			timeout=PATIENCE,
		)
	except requests.RequestException as raised:
		raise faults.Again(f"the account could not be reached: {raised}") from raised

	if answer.status_code == 200:
		return answer.json().get("message")
	try:
		body = answer.json()
	except ValueError:
		body = None
	raise faults.raised(
		endpoint,
		answer.status_code,
		faults.detail(body, answer.text),
		said=(body or {}).get("exc_type") if isinstance(body, dict) else None,
	)


def refresh() -> dict:
	"""Ask who we are and write down the answer.

	Runs daily and on demand. A failure is recorded next to the previous answer
	rather than over it: "we last heard this, and since then we have not been
	able to ask" is two facts and a screen wants both.
	"""
	held = frappe.get_single("Workspace Account")
	try:
		said = ask("onedesk.one_admin.proxy.hello") or {}
	except faults.Refused as refused:
		held.db_set("last_error", str(refused)[: faults.KEPT])
		return held.as_dict()

	standing = said.get("standing") or {}
	credits = said.get("credits") or {}
	held.db_set(
		{
			"tenant": said.get("tenant"),
			"workspace_name": said.get("workspace"),
			"status": said.get("status"),
			"domain": said.get("domain"),
			"jurisdiction": said.get("jurisdiction"),
			"cluster": said.get("cluster"),
			"plan": said.get("plan"),
			"seats": said.get("seats") or 0,
			"storage_bytes": said.get("storage_bytes") or 0,
			"storage_limit": said.get("storage_limit") or 0,
			"credits_balance": credits.get("balance") or 0,
			"credits_held": credits.get("held") or 0,
			"credits_expiring": credits.get("expiring") or 0,
			"credits_expires_on": credits.get("expires_on"),
			"owing": 1 if standing.get("owing") else 0,
			"days_left": standing.get("days_left"),
			"next_status": standing.get("next"),
			"last_heard": now_datetime(),
			"last_error": None,
		}
	)
	_keep(held, said.get("domains"))
	return held.as_dict()


def _keep(held, rows) -> None:
	"""Write down the addresses the administrator listed.

	A copy, so the screen draws without a round trip and keeps drawing through
	an outage. `rows` is None when the administrator did not send any — an older
	one, or a call that only asked for the account — and in that case the ones
	already written stay rather than being cleared, because an absent answer is
	not an answer of nothing.
	"""
	if rows is None:
		return
	held.set(
		"domains",
		[
			{
				"domain": one.get("domain"),
				"status": one.get("status"),
				"primary": 1 if one.get("primary") else 0,
				"given": 1 if one.get("given") else 0,
			}
			for one in rows
			if one.get("domain")
		],
	)
	held.save(ignore_permissions=True)


def nightly() -> None:
	"""Keep the cached answer from going stale on a workspace nobody asks about."""
	if configured():
		refresh()


@frappe.whitelist()
def mine() -> dict:
	"""What a screen draws, from the cache and without a round trip."""
	return frappe.get_single("Workspace Account").as_dict()


def put_url(key: str, size: int) -> dict:
	"""Ask for somewhere to put a file. The bytes go to R2, not to admin."""
	return ask("onedesk.one_admin.proxy.storage_put", key=key, size=size)


def get_url(key: str) -> dict:
	return ask("onedesk.one_admin.proxy.storage_get", key=key)


def drop(key: str) -> dict:
	return ask("onedesk.one_admin.proxy.storage_delete", key=key)


#: Who on a workspace may change what it is called. Not everybody who can read
#: the settings screen: a domain change moves where the login page lives, so it
#: belongs to whoever already administers the site.
MAY_RENAME = "System Manager"


@frappe.whitelist()
def credit_packs() -> list:
	"""What this workspace may buy, asked of the account.

	Not cached: a price list is the administrator's and a copy of one here is a
	price that goes stale the day it changes.
	"""
	_may_rename()
	return ask("onedesk.one_admin.proxy.credit_packs") or []


@frappe.whitelist()
def buy_credits(pack: str) -> dict:
	"""Somewhere to pay for a pack. The credit arrives by webhook, not here."""
	_may_rename()
	return ask("onedesk.one_admin.proxy.buy_credits", pack=pack)


def _may_rename() -> None:
	if MAY_RENAME not in frappe.get_roles():
		frappe.throw(
			frappe._("Only an administrator of this workspace can change its address."),
			frappe.PermissionError,
		)


def _after(rows):
	"""Write the administrator's answer into the account and hand it back."""
	held = frappe.get_single("Workspace Account")
	_keep(held, rows)
	return rows


@frappe.whitelist()
def domains() -> list:
	"""Every address this workspace answers at.

	Ours is first and is never removable. The rest are the customer's own, and
	each carries what press last said about it — which is the part that helps
	when one is not working.
	"""
	_may_rename()
	return _after(ask("onedesk.one_admin.proxy.domain_list") or [])


@frappe.whitelist()
def domains_refresh() -> list:
	"""Go and ask, rather than draw what was last known.

	The button beside the list. A domain goes live minutes after it is added and
	nothing tells the workspace, so there has to be something to press.
	"""
	_may_rename()
	return _after(ask("onedesk.one_admin.proxy.domain_refresh") or [])


@frappe.whitelist()
def domain_check(domain: str) -> dict:
	"""Whether the DNS is right, before claiming anything.

	Answers in press's own words, including the one about proxying: a name
	behind Cloudflare's orange cloud answers `server: cloudflare` to press's
	check and is refused until it is turned off. Relayed rather than reworded,
	because press's sentence names the fix.
	"""
	_may_rename()
	return ask("onedesk.one_admin.proxy.domain_check", domain=domain) or {}


@frappe.whitelist()
def domain_add(domain: str) -> dict:
	_may_rename()
	answer = ask("onedesk.one_admin.proxy.domain_add", domain=domain) or {}
	_after(ask("onedesk.one_admin.proxy.domain_list") or [])
	return answer


@frappe.whitelist()
def domain_drop(domain: str) -> dict:
	_may_rename()
	answer = ask("onedesk.one_admin.proxy.domain_drop", domain=domain) or {}
	_after(ask("onedesk.one_admin.proxy.domain_list") or [])
	return answer


@frappe.whitelist()
def domain_primary(domain: str) -> dict:
	"""Make one of them the address the workspace calls itself.

	This is the one that changes what the site believes rather than only what
	reaches it: press writes `host_name` into the site's config, so a link in an
	email starts using the new name.
	"""
	_may_rename()
	answer = ask("onedesk.one_admin.proxy.domain_primary", domain=domain) or {}
	_after(ask("onedesk.one_admin.proxy.domain_list") or [])
	return answer
