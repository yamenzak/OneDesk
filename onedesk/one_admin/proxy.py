"""The one door a tenant site knocks on, and how it proves who it is.

Everything a workspace is billed for comes through here: a signed URL to put a
file, a credit hold, a plan change, a domain. **Calls only ever go tenant to
admin.** Admin never calls a tenant site, which is what removes the dangerous
credential from this design — there is no admin key that opens every workspace,
because admin never needs to open one.

A tenant proves itself with the token `push_config` wrote into its own site
config at provision time. Only a hash of it is here. The comparison is
constant-time, and **every failure says the same thing**: an unknown workspace,
a wrong token and a suspended one are one sentence, because a caller who has
guessed one of the three should not be told which.

The endpoints are `allow_guest` and that is deliberate rather than an oversight.
The caller has no Frappe session here and should not have one — a login on the
admin site is a person, and this is a machine holding a bearer token. So Frappe's
own authentication is not in the path and ours is, which means ours has to be
the careful kind.

What is *not* here: anything that carries bytes. Admin checks, signs and records;
R2 and Cloudflare carry. A file never passes through this process.
"""

import hashlib
import hmac

import frappe
from frappe.rate_limiter import rate_limit
from frappe.utils import cint

from onedesk.one_admin import faults, site

#: The rungs a workspace is still served on. Live and Overdue, and nothing
#: below.
#:
#: Overdue is here because Overdue is defined as nothing happening to the
#: workspace — somebody is told and that is all. Leaving it out would mean a
#: failed card silently broke every upload on the same afternoon, which is the
#: grace period not existing.
#:
#: Suspended is out, and below that there is no site left to call. It costs
#: nothing to say so anyway: press has already deactivated a suspended site, so
#: a call from one is a call from a site that should not be running.
SERVING = ("Live", "Overdue")

#: Ours rather than `Authorization`, which Frappe's own API-key authentication
#: reads first and rejects anything in that is not `key:secret`.
HEADER = "X-One-Token"

#: Per tenant per minute, and not per IP: every tenant on one bench calls from
#: one address, so an IP limit would be a limit on the busiest neighbour. High
#: enough that a workspace doing real work never meets it, low enough that a
#: leaked token cannot be used to grind through the catalogue.
A_MINUTE = 60
CALLS_A_MINUTE = 120


def caller():
	"""The tenant making this call, or a refusal.

	Reads the slug from the request rather than taking it as an argument, so
	every endpoint gets the same check and none of them can be written to trust
	a slug a caller sent in the body.
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
	if held.status not in SERVING:
		_refuse()
	return held


def _offered_token() -> str:
	"""Our own header, because `Authorization` is already spoken for.

	A header rather than a parameter: a token in the body is a token in a
	traceback, in a slow-query log and in anything that echoes what it was sent.

	Not `Authorization`, though, and this was measured rather than reasoned:
	Frappe's own `validate_auth_via_api_keys` reads that header, sees the word
	token and splits the rest on a colon to get an API key and secret. A token
	of ours has no colon, so every call died with `InvalidAuthorizationToken`
	before reaching this module. A header of our own stays out of its way.
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
	raise frappe.AuthenticationError(frappe._("Not a workspace this site administers."))


@frappe.whitelist(allow_guest=True)
@rate_limit(key="tenant", limit=CALLS_A_MINUTE, seconds=A_MINUTE, ip_based=False)
def hello(database_bytes: int | None = None) -> dict:
	"""Who this workspace is and what it is allowed, in one call.

	`database_bytes` is the workspace's own measure of its database, sent
	along because the workspace can read it and admin cannot. It is shown
	and warned about, never billed: the sites are on our own servers, where
	Frappe Cloud sets no limit, so the limit is ours (quota.py).

	The tenant caches the answer in its own `Workspace Account`, so a screen
	showing a plan or a quota draws without a round trip and keeps drawing
	through an admin outage. That is why this returns the whole picture rather
	than answering one question — the alternative is a workspace making four
	calls to render a header.

	It returns what exists. A zero is a fact and an absence is the truth, so
	anything not built yet is left out rather than reported as nothing —
	`credits` arrived with the ledger and is a real number now.

	`standing` is the ladder: whether money is owed, and how many days are left
	before the next thing happens. It is here rather than behind a call of its
	own because a workspace that has to ask a second question to find out it is
	about to be suspended is a workspace that will not ask.
	"""
	tenant = caller()
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
	from onedesk.one_admin import billing, domains, ledger, lifecycle, offerings

	plan = (
		frappe.db.get_value("Offering", known.offering, ["label", "seats"], as_dict=True)
		if known.offering
		else None
	)
	return {
		"tenant": tenant.name,
		"status": tenant.status,
		"standing": lifecycle.standing(_tenant_doc(tenant)),
		"workspace": known.workspace_name,
		# Who paid for it: made its first administrator and invited, once, by a
		# workspace nobody administers yet (one/owner.py).
		"owner": known.owner_email,
		# Whose One account holds it now: who is billed and told (accounts.py).
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
		# Who its invoices are from, so its books can know us as a supplier.
		"seller": billing.seller(),
		"storage_bytes": known.storage_bytes or 0,
		"storage_limit": known.storage_limit or 0,
		# A sum over the ledger rather than a number anybody stored, which is
		# why it is safe to answer from here rather than keeping a copy on the
		# workspace that could disagree with its own history.
		# The last credits an operator gave, with their note, so the customer
		# hears why and not only that the number went up (one/account.py).
		"credits": {
			**ledger.standing(tenant.name),
			# Nothing to run low against on our own workspace, which is never
			# refused (house.py), so it is never told it is running low.
			"month": 0 if known.get("is_house") else _used_lately(tenant.name),
			"gift": ledger.last_gift(tenant.name),
		},
		# The addresses too, so the account screen is one call rather than two.
		# A workspace that asked only about its account still gets them, which
		# is what keeps the copy on its own site in step after an outage.
		"domains": domains.mine(_tenant_doc(tenant)),
		# What a customer's own name points at, as a CNAME: the name we gave the
		# workspace, which is what Cloudflare serves it from (domains.py).
		"dns_target": known.domain,
	}


@frappe.whitelist(allow_guest=True)
@rate_limit(key="tenant", limit=CALLS_A_MINUTE, seconds=A_MINUTE, ip_based=False)
def ai_run(
	action: str,
	text: str | None = None,
	model: str | None = None,
	extra: str | None = None,
	reference: str | None = None,
	turns: list | str | None = None,
	tools: list | str | None = None,
) -> dict:
	"""One action, run for this workspace and billed to it.

	`turns` is the conversation so far and `tools` are the ones the workspace is
	willing to run. Both arrive whole each round, because this is stateless: a
	model that wants to look something up is answered with what it asked for,
	the workspace runs the tool as whoever is signed in there, and calls back.

	`model` and `extra` are the workspace's own settings, sent with the call
	because they live on the workspace's site and admin never calls a workspace.
	Both are checked here rather than trusted: the model against what is
	offered and what the action needs, and the extra against a length, because
	what a tenant sends is what a tenant's administrator typed.

	The instruction the action carries is **not** sent — it is read here, from
	the administrator's own copy of the fixture, which is the copy a workspace
	cannot write.
	"""
	from onedesk.one_admin import actions

	tenant = caller()
	try:
		return actions.run(
			tenant.name,
			action,
			text,
			model=model,
			extra=extra,
			reference=reference,
			turns=frappe.parse_json(turns) if isinstance(turns, str) else turns,
			tools=frappe.parse_json(tools) if isinstance(tools, str) else tools,
		)
	except faults.Refused as raised:
		# Thrown rather than allowed to propagate, because frappe answers an
		# unhandled exception with a body carrying only `exc_type` — so the
		# sentence that says *why* ("this has gone five rounds", "that model is
		# not offered") never reaches the workspace, and the panel has nothing
		# to show but the endpoint's name. `Again` is a subclass and keeps its
		# own name, so the caller can still tell retryable from permanent.
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


@frappe.whitelist(allow_guest=True)
@rate_limit(key="tenant", limit=CALLS_A_MINUTE, seconds=A_MINUTE, ip_based=False)
def billing_portal(back: str) -> dict:
	"""Stripe's billing portal for this workspace."""
	from onedesk.one_admin import billing

	return {"url": billing.portal(caller().name, back)}


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
def ai_models(needs: str) -> list[dict]:
	"""The models this workspace may pick for an action needing this capability.

	A workspace holds no catalogue — the models, their prices and whether they
	are offered all live here — so a settings screen asks for the list rather
	than keeping a copy that would go stale the day a provider withdrew one.
	"""
	from onedesk.one_admin import actions

	caller()
	return actions.offered(needs)


@frappe.whitelist(allow_guest=True)
@rate_limit(key="tenant", limit=CALLS_A_MINUTE, seconds=A_MINUTE, ip_based=False)
def ai_models_for(needs: str | list) -> dict:
	"""The models for several capabilities at once, so a screen listing every
	action asks once rather than once per capability."""
	from onedesk.one_admin import actions

	caller()
	return {one: actions.offered(one) for one in sorted(set(frappe.parse_json(needs) or []))}


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
		frappe.throw(frappe._("Those are not this workspace's addresses."), frappe.PermissionError)
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
