"""The one door a tenant site knocks on, and how it proves who it is.

Calls only ever go tenant to admin. A tenant proves itself with the token
`push_config` wrote into its site config; every failure says the same thing.
"""

import hashlib
import hmac

import frappe
from frappe.rate_limiter import rate_limit
from frappe.utils import cint

from onedesk.one_admin import faults, site

SERVING = ("Live", "Overdue")

INTRODUCED = (*SERVING, "Provisioning")

HEADER = "X-One-Token"

A_MINUTE = 60
CALLS_A_MINUTE = 120
AN_HOUR = 3600
CLAIMS_AN_HOUR = 20


def caller(serving: tuple = SERVING):
	"""The tenant making this call, or a refusal.

	Reads the slug from the request rather than taking it as an argument, so
	every endpoint gets the same check and none of them can be written to trust
	a slug a caller sent in the body. `serving` is the statuses that may call.
	"""
	site.require_admin()
	slug = frappe.form_dict.get("tenant")
	offered = _offered_token()
	if not slug or not offered:
		_refuse()

	held = frappe.db.get_value(
		"Tenant", slug, ["name", "status", "token_hash"], as_dict=True
	)
	if not held or not held.token_hash:
		_refuse()
	if not hmac.compare_digest(held.token_hash, _hashed(offered)):
		_refuse()
	if held.status not in serving:
		_refuse()
	return held


def _offered_token() -> str:
	"""Our own header, because `Authorization` is already spoken for.

	A header rather than a parameter, so the token is not in a traceback or a log;
	not `Authorization`, which Frappe's API-key authentication reads first.
	"""
	return (frappe.get_request_header(HEADER) or "").strip()


def _hashed(token: str) -> str:
	return hashlib.sha256(token.encode()).hexdigest()


def _refuse():
	"""One sentence for every way of being wrong.

	No log either. A failed call here is unauthenticated by definition, so
	logging one is a way for anybody who can reach this site to fill the error
	log at no cost to themselves.
	"""
	raise frappe.AuthenticationError(frappe._("This site doesn't manage this workspace."))


@frappe.whitelist(allow_guest=True)
@rate_limit(key="tenant", limit=CALLS_A_MINUTE, seconds=A_MINUTE, ip_based=False)
def hello(database_bytes: int | None = None) -> dict:
	"""Who this workspace is and what it is allowed, in one call.

	The tenant caches the whole answer in its own `Workspace Account`, so it
	returns the whole picture, including `standing`, the ladder. It returns what
	exists: anything not built yet is left out. A workspace still being built
	may ask, because its build's `invite_owner` step is this call.
	"""
	tenant = caller(INTRODUCED)
	if database_bytes is not None:
		frappe.db.set_value("Tenant", tenant.name, "database_bytes", cint(database_bytes), update_modified=False)
	known = frappe.db.get_value(
		"Tenant",
		tenant.name,
		[
			"account",
			"seats",
			"database_bytes",
			"database_limit",
			"workspace_name",
			"domain",
			"primary_domain",
			"jurisdiction",
			"cluster",
			"live_on",
			"offering",
			"storage_bytes",
			"storage_limit",
			"owner_email",
			"is_house",
		],
		as_dict=True,
	)
	from onedesk.one_admin import billing, closing, domains, ledger, lifecycle, offerings

	plan = (
		frappe.db.get_value("Offering", known.offering, ["label", "seats"], as_dict=True)
		if known.offering
		else None
	)
	return {
		"tenant": tenant.name,
		"status": tenant.status,
		"standing": lifecycle.standing(_tenant_doc(tenant)),
		"closing": closing.when(_tenant_doc(tenant)),
		"workspace": known.workspace_name,
		"owner": known.owner_email,
		"billed_to": known.get("account"),
		"domain": known.primary_domain or known.domain,
		"given_domain": known.domain,
		"jurisdiction": known.jurisdiction,
		"cluster": known.cluster,
		"live_on": str(known.live_on) if known.live_on else None,
		"plan": plan.label if plan else None,
		"seats": known.seats or (plan.seats if plan else None),
		"plan_key": known.offering,
		"monthly": billing.monthly(_tenant_doc(tenant)),
		"currency": offerings.currency(),
		"database_bytes": known.database_bytes or 0,
		"database_limit": known.database_limit or 0,
		"add_ons": _add_ons(tenant.name),
		"seller": billing.seller(),
		"storage_bytes": known.storage_bytes or 0,
		"storage_limit": known.storage_limit or 0,
		"credits": {
			**ledger.standing(tenant.name),
			"month": 0 if known.get("is_house") else _used_lately(tenant.name),
			"gift": ledger.last_gift(tenant.name),
		},
		"domains": domains.mine(_tenant_doc(tenant)),
		"dns_target": known.domain,
	}


@frappe.whitelist(allow_guest=True)
@rate_limit(key="tenant", limit=CALLS_A_MINUTE, seconds=A_MINUTE, ip_based=False)
def ai_run(
	action: str,
	text: str | None = None,
	tier: str | None = None,
	reference: str | None = None,
	turns: list | str | None = None,
	tools: list | str | None = None,
) -> dict:
	"""One job, run for this workspace and billed to it.

	Stateless: `turns` and `tools` arrive whole each round. A workspace says
	its tier and nothing about the model; what the model is told is
	one_ai/jobs.py's, never sent.
	"""
	from onedesk.one_admin import actions

	tenant = caller()
	try:
		return actions.run(
			tenant.name,
			action,
			text,
			tier=tier,
			reference=reference,
			turns=frappe.parse_json(turns) if isinstance(turns, str) else turns,
			tools=frappe.parse_json(tools) if isinstance(tools, str) else tools,
		)
	except faults.Refused as raised:
		frappe.throw(str(raised), exc=type(raised))


@frappe.whitelist(allow_guest=True)
@rate_limit(key="tenant", limit=CALLS_A_MINUTE, seconds=A_MINUTE, ip_based=False)
def ai_read(
	action: str,
	state: str,
	asked: dict | str,
	tier: str | None = None,
	reference: str | None = None,
	on: str | None = None,
) -> dict:
	"""One reading job (sorting or reading fields) for this workspace, billed
	to it. A workspace names the job and sends the text and its questions;
	the model is the door's."""
	from onedesk.one_admin import actions

	tenant = caller()
	try:
		return actions.read(
			tenant.name, action, state, frappe.parse_json(asked) if isinstance(asked, str) else asked, tier=tier, reference=reference, on=on
		)
	except faults.Refused as raised:
		frappe.throw(str(raised), exc=type(raised))


@frappe.whitelist(allow_guest=True)
@rate_limit(key="tenant", limit=CALLS_A_MINUTE, seconds=A_MINUTE, ip_based=False)
def ai_search_state() -> dict:
	"""Whether this workspace has its own search instance yet. Free."""
	from onedesk.one_admin import search

	return {"live": bool(search.instance_of(caller().name))}


@frappe.whitelist(allow_guest=True)
@rate_limit(key="tenant", limit=CALLS_A_MINUTE, seconds=A_MINUTE, ip_based=False)
def ai_search(query: str, mode: str = "keyword", most: int = 10) -> dict:
	"""This workspace's own search instance, asked by keyword or by meaning
	and billed to it (one_admin/search.py). A workspace with none is told so
	and searches as it did."""
	from onedesk.one_admin import search

	tenant = caller()
	try:
		return search.find(tenant.name, query, mode, int(most or 10))
	except faults.Refused as raised:
		frappe.throw(str(raised), exc=type(raised))


@frappe.whitelist(allow_guest=True)
@rate_limit(key="tenant", limit=CALLS_A_MINUTE, seconds=A_MINUTE, ip_based=False)
def ai_web_search(query: str, most: int = 5) -> dict:
	"""One web search for this workspace, the question alone, billed to it
	(one_admin/web.py). Asked only while its web search service is on."""
	from onedesk.one_admin import web

	tenant = caller()
	try:
		return web.find(tenant.name, query, int(most or 5))
	except faults.Refused as raised:
		frappe.throw(str(raised), exc=type(raised))


@frappe.whitelist(allow_guest=True)
@rate_limit(key="tenant", limit=CALLS_A_MINUTE, seconds=A_MINUTE, ip_based=False)
def ai_embed(texts: list | str) -> dict:
	"""Texts as vectors, for this workspace's search by meaning, billed to it."""
	from onedesk.one_admin import actions

	tenant = caller()
	try:
		return actions.embed(tenant.name, frappe.parse_json(texts) if isinstance(texts, str) else texts)
	except faults.Refused as raised:
		frappe.throw(str(raised), exc=type(raised))


@frappe.whitelist(allow_guest=True)
@rate_limit(key="tenant", limit=CALLS_A_MINUTE, seconds=A_MINUTE, ip_based=False)
def credit_packs() -> list[dict]:
	"""What a workspace may buy. A price list, not a calculator."""
	from onedesk.one_admin import topup

	caller()
	return topup.packs()


@frappe.whitelist(allow_guest=True)
@rate_limit(key="tenant", limit=CALLS_A_MINUTE, seconds=A_MINUTE, ip_based=False)
def buy_credits(pack: str) -> dict:
	"""Somewhere for this workspace to pay. Nothing is granted here.

	The grant is the webhook's, after Stripe says the money moved — which is the
	same rule as a signup, for the same reason: a workspace that could grant
	itself credit by opening a page is a workspace that never pays.
	"""
	from onedesk.one_admin import topup

	return topup.buy(caller().name, pack)


@frappe.whitelist(allow_guest=True)
@rate_limit(key="tenant", limit=CALLS_A_MINUTE, seconds=A_MINUTE, ip_based=False)
def plans_offered(seats_used: int = 0) -> dict:
	"""What this workspace has, and the plans and add-ons it could have."""
	from onedesk.one_admin import billing

	return billing.offered(caller().name, cint(seats_used))


@frappe.whitelist(allow_guest=True)
@rate_limit(key="tenant", limit=CALLS_A_MINUTE, seconds=A_MINUTE, ip_based=False)
def plans_quote(needs: str | dict, seats_used: int = 0) -> dict:
	"""Every plan with the add-ons that bring it up to `needs`, cheapest first."""
	from onedesk.one_admin import billing

	return billing.quote(caller().name, frappe.parse_json(needs) or {}, cint(seats_used))


@frappe.whitelist(allow_guest=True)
@rate_limit(key="tenant", limit=CALLS_A_MINUTE, seconds=A_MINUTE, ip_based=False)
def plans_take(plan: str, extras: str | dict | None = None, seats_used: int = 0) -> dict:
	"""Make this workspace's subscription this plan with exactly these add-ons."""
	from onedesk.one_admin import billing

	return billing.take(caller().name, plan, frappe.parse_json(extras) or {}, cint(seats_used))


@frappe.whitelist(allow_guest=True)
@rate_limit(key="tenant", limit=CALLS_A_MINUTE, seconds=A_MINUTE, ip_based=False)
def billing_invoices() -> dict:
	"""This workspace's invoices, and who they are from."""
	from onedesk.one_admin import billing

	return billing.invoices(caller().name)


@frappe.whitelist(allow_guest=True)
@rate_limit(key="tenant", limit=CALLS_A_MINUTE, seconds=A_MINUTE, ip_based=False)
def billing_invoice(invoice: str) -> dict:
	"""One of this workspace's invoices with its lines."""
	from onedesk.one_admin import billing

	return billing.invoice(caller().name, invoice)


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(key="tenant", limit=CALLS_A_MINUTE, seconds=A_MINUTE, ip_based=False)
def billed_to(email: str, by: str | None = None) -> dict:
	"""Move this workspace to the One account for this address. The workspace
	asks only for its administrators (one/account.py, move_billing)."""
	from onedesk.one_admin import accounts

	return {"billed_to": accounts.move(caller().name, email, by)}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(key="tenant", limit=CALLS_A_MINUTE, seconds=A_MINUTE, ip_based=False)
def close(by: str) -> dict:
	"""Close this workspace in a fortnight. The workspace asks only for the
	person it is billed to, who confirmed with their password (one_account/closing.py)."""
	from onedesk.one_admin import closing

	return closing.ask(caller().name, by)


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(key="tenant", limit=CALLS_A_MINUTE, seconds=A_MINUTE, ip_based=False)
def withdraw_closing(by: str) -> dict:
	"""Withdraw the closing, before its day."""
	from onedesk.one_admin import closing

	return closing.keep(caller().name, by)


@frappe.whitelist(allow_guest=True)
@rate_limit(key="tenant", limit=CALLS_A_MINUTE, seconds=A_MINUTE, ip_based=False)
def billing_portal(back: str) -> dict:
	"""Stripe's billing portal for this workspace."""
	from onedesk.one_admin import billing

	return {"url": billing.portal(caller().name, back)}


@frappe.whitelist(allow_guest=True)
@rate_limit(key="tenant", limit=CALLS_A_MINUTE, seconds=A_MINUTE, ip_based=False)
def billing_card() -> dict:
	"""A checkout that takes a new card, for the workspace to draw."""
	from onedesk.one_admin import billing

	return {"checkout": billing.card(caller().name)}


def _add_ons(tenant: str) -> list[dict]:
	"""What is on the workspace's plan, as it shows them."""
	rows = frappe.get_all(
		"Tenant Add-on",
		filters={"parent": tenant, "parenttype": "Tenant"},
		fields=["offering", "quantity"],
		order_by="idx",
	)
	sold = {
		one.name: one
		for one in frappe.get_all(
			"Offering", filters={"name": ["in", [one.offering for one in rows] or [""]]}, fields=["name", "label", "amount"]
		)
	}
	return [
		{
			"offering": one.offering,
			"label": (sold.get(one.offering) or {}).get("label") or one.offering,
			"quantity": one.quantity or 1,
			"amount": (sold.get(one.offering) or {}).get("amount") or 0,
		}
		for one in rows
	]


def _used_lately(tenant: str) -> float:
	"""Credits spent in the last thirty days, which is what "running low" is
	measured against: a balance is low for what this workspace uses, not for a
	number anybody picked."""
	from frappe.utils import add_days, getdate

	from onedesk.one_admin import ledger

	today = getdate()
	whole = ledger.usage(add_days(today, -30), add_days(today, 1), [], tenant=tenant)
	return float((whole[0] or {}).get("credits") or 0) if whole else 0.0


@frappe.whitelist(allow_guest=True)
@rate_limit(key="tenant", limit=CALLS_A_MINUTE, seconds=A_MINUTE, ip_based=False)
def ai_usage(start: str, end: str) -> dict:
	"""What this workspace has left and what it spent, for its own credits screen.

	Its own rows only: `caller()` names the workspace from its token, never from
	anything in the body. By model and by reference — the conversation or action
	a call was made for — because the workspace can say whose those are and the
	account cannot.
	"""
	from frappe.utils import add_days, getdate

	from onedesk.one_admin import ledger

	tenant = caller().name
	start, end = getdate(start), add_days(getdate(end), 1)
	whole = ledger.usage(start, end, [], tenant=tenant)
	return {
		"standing": ledger.standing(tenant),
		"total": whole[0] if whole else {},
		"days": ledger.daily(tenant, start, end),
		"arrived": [
			{
				**one,
				"creation": str(one.creation),
				"expires_on": str(one.expires_on) if one.expires_on else None,
			}
			for one in ledger.arrived(tenant, start, end)
		],
		"models": ledger.usage(start, end, ["why"], tenant=tenant),
		"references": ledger.usage(start, end, ["reference"], tenant=tenant),
		"actions": ledger.usage(start, end, ["action"], tenant=tenant),
	}


@frappe.whitelist(allow_guest=True)
@rate_limit(key="tenant", limit=CALLS_A_MINUTE, seconds=A_MINUTE, ip_based=False)
def ai_tiers() -> list[dict]:
	"""What a usual answer in the panel costs at each tier, in credits, for
	AICenter to show beside the choice."""
	from onedesk.one_admin import gateway, pricing
	from onedesk.one_ai import models

	caller()
	money = gateway._money()
	usual = [pricing.Use("input", "text", "tokens", TYPICAL_IN), pricing.Use("output", "text", "tokens", TYPICAL_OUT)]
	out = []
	for tier in models.TIERS:
		model = models.pick("talk", tier)[0]
		try:
			credits = pricing.bill(models.rates(model), usual, money["markup"], money["per_dollar"]).credits
		except (pricing.Unpriceable, frappe.ValidationError):
			credits = None
		out.append({"tier": tier, "credits": credits})
	return out


# A usual answer in the panel: the conversation and what was looked up in,
# a few sentences out.
TYPICAL_IN, TYPICAL_OUT = 6000, 400


@frappe.whitelist(allow_guest=True)
@rate_limit(key="tenant", limit=CALLS_A_MINUTE, seconds=A_MINUTE, ip_based=False)
def storage_put(key: str, size: int = 0) -> dict:
	"""A signed URL to put one object, if the workspace has room for it.

	The key a caller sends is a suffix and never a path: `keys.under` puts it
	inside this workspace's prefix or refuses, so there is no key a caller can
	send that names somebody else's object.
	"""
	from onedesk.one_admin import storage

	return storage.put_url(_tenant_doc(caller()), key, size)


@frappe.whitelist(allow_guest=True)
@rate_limit(key="tenant", limit=CALLS_A_MINUTE, seconds=A_MINUTE, ip_based=False)
def storage_get(key: str, filename: str | None = None, inline: int = 1) -> dict:
	from onedesk.one_admin import storage

	return storage.get_url(_tenant_doc(caller()), key, filename=filename, inline=bool(int(inline)))


@frappe.whitelist(allow_guest=True)
@rate_limit(key="tenant", limit=CALLS_A_MINUTE, seconds=A_MINUTE, ip_based=False)
def storage_delete(key: str) -> dict:
	from onedesk.one_admin import storage

	return storage.remove(_tenant_doc(caller()), key)


@frappe.whitelist(allow_guest=True)
@rate_limit(key="tenant", limit=CALLS_A_MINUTE, seconds=A_MINUTE, ip_based=False)
def mail_waiting(after: str | None = None) -> list[dict]:
	"""Mail that arrived for this workspace and has not been read, oldest first."""
	from onedesk.one_admin import storage

	return storage.mail_waiting(_tenant_doc(caller()), after)


@frappe.whitelist(allow_guest=True)
@rate_limit(key="tenant", limit=CALLS_A_MINUTE, seconds=A_MINUTE, ip_based=False)
def mail_names(names: str | list) -> list[str]:
	"""The names this workspace receives mail for, so the Worker refuses the
	rest while the sender is still connected. Every name is this workspace's
	own — `<slug>` or `<name>.<slug>` — or the call is refused."""
	from onedesk.one_admin import cloudflare
	from onedesk.one_mail import addresses

	tenant = _tenant_doc(caller())
	names = frappe.parse_json(names) if isinstance(names, str) else names
	wanted = sorted({str(one).strip().lower() for one in names or []})
	if not wanted or not all(addresses.is_workspace_name(one, tenant.slug) for one in wanted):
		frappe.throw(frappe._("Those addresses aren't on this workspace."), frappe.PermissionError)
	record = cloudflare.mail_record(tenant.slug)
	if not record:
		frappe.throw(frappe._("This workspace has no mail route yet."))
	record["names"] = wanted
	cloudflare.mail_route(tenant.slug, record)
	return wanted


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(key="tenant", limit=CALLS_A_MINUTE, seconds=A_MINUTE, ip_based=False)
def mail_send(sender: str, recipient: str, message: str) -> dict:
	"""One message, as the workspace's Email Queue built it, from one of its
	own addresses on the mail domain. See mailing.py for what is checked."""
	from onedesk.one_admin import mailing

	return mailing.send(_tenant_doc(caller()), sender, recipient, message)


def _tenant_doc(tenant):
	"""The whole record, once the caller has been established.

	`caller` reads three fields because authenticating should not cost a document
	load; anything that goes on to do real work wants the rest.
	"""
	return frappe.get_doc("Tenant", tenant.name)


@frappe.whitelist(allow_guest=True)
@rate_limit(key="tenant", limit=CALLS_A_MINUTE, seconds=A_MINUTE, ip_based=False)
def domain_list() -> list:
	"""Every name this workspace can be reached at.

	Read from our own rows rather than press, so opening the screen costs one
	call and works when press is slow. `domain_refresh` is what goes and asks.
	"""
	from onedesk.one_admin import domains

	return domains.mine(_tenant_doc(caller()))


@frappe.whitelist(allow_guest=True)
@rate_limit(key="tenant", limit=CALLS_A_MINUTE, seconds=A_MINUTE, ip_based=False)
def domain_refresh() -> list:
	from onedesk.one_admin import domains

	return domains.refresh(_tenant_doc(caller()))


@frappe.whitelist(allow_guest=True)
@rate_limit(key="tenant", limit=CALLS_A_MINUTE, seconds=A_MINUTE, ip_based=False)
def domain_add(domain: str) -> dict:
	from onedesk.one_admin import domains

	return domains.add(_tenant_doc(caller()), domain)


@frappe.whitelist(allow_guest=True)
@rate_limit(key="tenant", limit=CALLS_A_MINUTE, seconds=A_MINUTE, ip_based=False)
def domain_drop(domain: str) -> dict:
	from onedesk.one_admin import domains

	return domains.drop(_tenant_doc(caller()), domain)


@frappe.whitelist(allow_guest=True)
@rate_limit(key="tenant", limit=CALLS_A_MINUTE, seconds=A_MINUTE, ip_based=False)
def domain_primary(domain: str) -> dict:
	from onedesk.one_admin import domains

	return domains.make_primary(_tenant_doc(caller()), domain)


@frappe.whitelist(allow_guest=True)
@rate_limit(key="tenant", limit=CLAIMS_AN_HOUR, seconds=AN_HOUR, ip_based=False)
def app_claim(code: str, by: str | None = None) -> dict:
	"""A private app's code, typed in the workspace's Apps (one_admin/private.py)."""
	tenant = caller()
	from onedesk.one_admin import private

	return private.claim(tenant.name, code, by)


@frappe.whitelist(allow_guest=True)
@rate_limit(key="tenant", limit=CALLS_A_MINUTE, seconds=A_MINUTE, ip_based=False)
def private_apps() -> list[dict]:
	"""The private apps this workspace has claimed, and how far each has got."""
	tenant = caller()
	from onedesk.one_admin import private

	return private.mine(tenant.name)
