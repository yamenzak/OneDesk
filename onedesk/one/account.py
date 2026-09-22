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
	raise faults.raised(endpoint, answer.status_code, faults.detail(body, answer.text))


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

	held.db_set(
		{
			"tenant": said.get("tenant"),
			"workspace_name": said.get("workspace"),
			"status": said.get("status"),
			"domain": said.get("domain"),
			"jurisdiction": said.get("jurisdiction"),
			"cluster": said.get("cluster"),
			"last_heard": now_datetime(),
			"last_error": None,
		}
	)
	return held.as_dict()


def nightly() -> None:
	"""Keep the cached answer from going stale on a workspace nobody asks about."""
	if configured():
		refresh()


@frappe.whitelist()
def mine() -> dict:
	"""What a screen draws, from the cache and without a round trip."""
	return frappe.get_single("Workspace Account").as_dict()
