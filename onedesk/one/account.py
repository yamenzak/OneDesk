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
from frappe.rate_limiter import rate_limit
from frappe.utils import add_days, date_diff, flt, formatdate, getdate, now_datetime, today

from onedesk.one import roles
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


#: How long an AI run may take on admin: the account waits on the provider for
#: up to its own sixty seconds, or 110 for a call that thinks
#: (gateway.THOUGHT), so a caller giving up at ten gave up on answers that
#: were on their way — a drafted appraisal is longer than a lookup.
PATIENCE_FOR = {"onedesk.one_admin.proxy.ai_run": 120}


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
			timeout=PATIENCE_FOR.get(endpoint, PATIENCE),
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
	before = held.as_dict()
	try:
		said = ask("onedesk.one_admin.proxy.hello", database_bytes=database_bytes()) or {}
	except faults.Refused as refused:
		held.db_set("last_error", str(refused)[: faults.KEPT])
		return held.as_dict()

	standing = said.get("standing") or {}
	credits = said.get("credits") or {}
	held.db_set(
		{
			"tenant": said.get("tenant"),
			"workspace_name": said.get("workspace"),
			"billed_to": said.get("billed_to"),
			"status": said.get("status"),
			"domain": said.get("domain"),
			"dns_target": said.get("dns_target"),
			"jurisdiction": said.get("jurisdiction"),
			"cluster": said.get("cluster"),
			"plan": said.get("plan"),
			"seats": said.get("seats") or 0,
			"plan_key": said.get("plan_key"),
			"monthly": said.get("monthly") or 0,
			"plan_currency": said.get("currency"),
			"database_bytes": said.get("database_bytes") or 0,
			"database_limit": said.get("database_limit") or 0,
			"storage_bytes": said.get("storage_bytes") or 0,
			"storage_limit": said.get("storage_limit") or 0,
			"credits_balance": credits.get("balance") or 0,
			"credits_held": credits.get("held") or 0,
			"credits_month": credits.get("month") or 0,
			"credits_expiring": credits.get("expiring") or 0,
			"credits_expires_on": credits.get("expires_on"),
			"owing": 1 if standing.get("owing") else 0,
			"days_left": standing.get("days_left"),
			"next_status": standing.get("next"),
			"closing_on": (said.get("closing") or {}).get("closing_on"),
			"deleted_on": (said.get("closing") or {}).get("deleted_on"),
			"last_heard": now_datetime(),
			"last_error": None,
		}
	)
	_keep(held, said.get("domains"), said.get("add_ons"))
	_tell(before, held, credits.get("gift"))
	# A new workspace's first administrator is whoever paid for it (one/owner.py).
	from onedesk.one import owner

	owner.arrive(said)
	return held.as_dict()


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=5, seconds=60)
def wake() -> dict:
	"""Ask the administrator who this workspace is, now: the admin site's last
	step of a build calls this, so the owner's invitation leaves as the build
	finishes (one/owner.py). It takes nothing and trusts nobody: all it does
	is make this site ask, with its own token, and it says only whether the
	workspace has an administrator after."""
	if not configured():
		return {"administered": False}
	frappe.set_user("Administrator")
	try:
		refresh()
	finally:
		frappe.set_user("Guest")
	return {"administered": bool(roles.administrators())}


#: A balance under this share of the last thirty days' use is running low:
#: about three days left at the rate the workspace spends.
LOW = 0.1

#: How close to full storage is before the administrators hear of it.
NEARLY_FULL = 0.9

#: How many days before credits expire the administrators hear of it.
EXPIRY_NOTICE = 7


def _tell(before, after, gift: dict | None = None) -> None:
	"""What changed since the account was last asked, told to the workspace's
	administrators (one/notifications.py). Each is said when a line is crossed
	rather than while it stays crossed, so a nightly refresh does not repeat
	itself; the two told by date remember the date they were told of."""
	from onedesk.one import notify

	# Credits One gave by hand are told once each, with the operator's note.
	given = gift and _once("gift", gift.get("entry") or "")
	if not before.get("last_heard"):
		# The first answer is where the workspace starts, not a change.
		return
	people = _administrators()
	if not people:
		return
	told = {"link": PAGE, "sender": "Administrator"}

	was, now = flt(before.get("credits_balance")), flt(after.credits_balance)
	month = flt(after.credits_month)
	if month and now < month * LOW <= was:
		slots = {"balance": _number(now), "days": max(0, int(now / (month / 30)))}
		notify.notify("Credits Running Low", people, **told, **slots)
		for email, lang in _addresses(people):
			notify.mail("Credits Running Low", email, lang=lang, **slots)
	if given:
		from markupsafe import Markup, escape

		said = [frappe._("A note from One: {0}").format(gift["why"])] if gift.get("why") else []
		if gift.get("expires_on"):
			said.append(frappe._("They expire on {0}.").format(formatdate(gift["expires_on"])))
		note = Markup("<br><br>") + escape(" ".join(said)) if said else ""
		notify.notify("Credits Added", people, **told, balance=_number(now), note=note)
	elif now > was + 0.5:
		notify.notify("Credits Added", people, **told, balance=_number(now), note="")

	expires_on = after.credits_expires_on
	if flt(after.credits_expiring) and expires_on:
		left = date_diff(expires_on, today())
		if 0 <= left <= EXPIRY_NOTICE and _once("expiring", str(expires_on)):
			notify.notify(
				"Credits Expiring",
				people,
				**told,
				credits=_number(after.credits_expiring),
				date=formatdate(expires_on),
			)

	limit = flt(after.storage_limit)
	if limit and flt(before.get("storage_bytes")) < limit * NEARLY_FULL <= flt(after.storage_bytes):
		from onedesk.one.heads import size

		slots = {"used": size(after.storage_bytes), "limit": size(limit)}
		notify.notify("Storage Nearly Full", people, **told, **slots)
		for email, lang in _addresses(people):
			notify.mail("Storage Nearly Full", email, lang=lang, **slots)

	limit = flt(after.database_limit)
	if limit and flt(before.get("database_bytes")) < limit * NEARLY_FULL <= flt(after.database_bytes):
		from onedesk.one.heads import size

		slots = {"used": size(after.database_bytes), "limit": size(limit)}
		notify.notify("Database Nearly Full", people, **told, **slots)
		for email, lang in _addresses(people):
			notify.mail("Database Nearly Full", email, lang=lang, **slots)

	_tell_domains(before.get("domains") or [], [one.as_dict() for one in after.domains], after.dns_target)

	if after.owing and after.next_status and after.days_left is not None:
		on = formatdate(add_days(today(), after.days_left))
		if _once("overdue", on):
			notify.notify("Payment Overdue", people, **told, date=on)
			for email, lang in _addresses(people):
				notify.mail("Payment Overdue", email, lang=lang, date=on)


def _once(what: str, value: str) -> bool:
	"""Whether `what` has not yet been told for `value`, and remember it has."""
	key = f"one_account_told_{what}"
	if frappe.db.get_default(key) == value:
		return False
	frappe.db.set_default(key, value)
	return True


def _number(value) -> str:
	return frappe.utils.fmt_money(value, precision=0)


def _administrators() -> list[str]:
	from onedesk.one.settings import NOT_PEOPLE

	return [one for one in roles.administrators() if one not in NOT_PEOPLE]


def _addresses(people) -> list[tuple[str, str]]:
	"""Each person's address and language, for what is always mailed."""
	return [
		(one.email, one.language)
		for one in frappe.get_all("User", filters={"name": ["in", people]}, fields=["email", "language"])
		if one.email
	]


#: How far back the ledger on Plan and Credits goes.
LEDGER_DAYS = 90


def ledger() -> list[dict] | None:
	"""Where the credits came from and where they went, newest first: each
	grant and refund on a line of its own, and what OneAI used summed by day,
	because the account keeps a spend per call and that is the wrong thing to
	read. Asked every time, since the ledger is the account's and a copy would
	be a second history. None when the account cannot be reached."""
	from frappe import _

	end = getdate(today())
	start = add_days(end, -(LEDGER_DAYS - 1))
	try:
		said = ask("onedesk.one_admin.proxy.ai_usage", start=str(start), end=str(end)) or {}
	except faults.Refused:
		return None
	came = {
		"Purchase": lambda one: _("Bought {0}").format(one.get("why") or _("credits")),
		"Plan": lambda one: (
			_("The plan's monthly credits, until {0}").format(formatdate(one.get("expires_on")))
			if one.get("expires_on")
			else _("The plan's monthly credits")
		),
		"Operator": lambda _one: _("Given by One"),
	}
	rows = [
		{
			"on": str(one.get("creation"))[:10],
			"what": _("Refunded")
			if one.get("kind") == "Refund"
			else came.get(one.get("source"), lambda _one: _("Added"))(one),
			"came": flt(one.get("credits")),
		}
		for one in said.get("arrived") or []
	]
	rows += [
		{
			"on": str(one.get("day"))[:10],
			"what": _("Used by OneAI, one call")
			if one.get("calls") == 1
			else _("Used by OneAI, {0} calls").format(one.get("calls")),
			"went": flt(one.get("credits")),
			"day": str(one.get("day"))[:10],
		}
		for one in said.get("days") or []
	]
	# Newest first; on one day, what came in above what went out.
	return sorted(rows, key=lambda one: (one["on"], "came" in one), reverse=True)


#: Where every one of those leads.
PAGE = "/desk/workspace-settings?section=plan"


@frappe.whitelist(methods=["POST"])
def check_again() -> dict:
	"""Ask the account now rather than tonight: after paying, or when the
	page says its numbers are old."""
	roles.require()
	refresh()
	return {"ok": True}


def database_bytes() -> int:
	"""How big this workspace's database is, as MariaDB says: its tables and
	their indexes. Frappe reports it in MB."""
	try:
		return int(float(frappe.db.get_database_size() or 0) * 1024 * 1024)
	except Exception:
		return 0


def _keep(held, rows, add_ons=None) -> None:
	"""Write down the addresses the administrator listed.

	A copy, so the screen draws without a round trip and keeps drawing through
	an outage. `rows` is None when the administrator did not send any — an older
	one, or a call that only asked for the account — and in that case the ones
	already written stay rather than being cleared, because an absent answer is
	not an answer of nothing.
	"""
	if add_ons is not None:
		held.set(
			"add_ons",
			[
				{
					"offering": one.get("offering"),
					"label": one.get("label"),
					"quantity": one.get("quantity") or 1,
					"amount": one.get("amount") or 0,
				}
				for one in add_ons
			],
		)
		if rows is None:
			held.save(ignore_permissions=True)
	if rows is None:
		return
	held.set(
		"domains",
		[
			{
				"domain": one.get("domain"),
				"status": one.get("status"),
				"problem": one.get("problem"),
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


def put_url(key: str, size: int) -> dict:
	"""Ask for somewhere to put a file. The bytes go to R2, not to admin."""
	return ask("onedesk.one_admin.proxy.storage_put", key=key, size=size)


def get_url(key: str, filename: str | None = None, inline: bool = True) -> dict:
	return ask("onedesk.one_admin.proxy.storage_get", key=key, filename=filename, inline=int(inline))


def drop(key: str) -> dict:
	return ask("onedesk.one_admin.proxy.storage_delete", key=key)


@frappe.whitelist()
def credit_packs() -> list:
	"""What this workspace may buy, asked of the account.

	Not cached: a price list is the administrator's and a copy of one here is a
	price that goes stale the day it changes.
	"""
	roles.require()
	return ask("onedesk.one_admin.proxy.credit_packs") or []


@frappe.whitelist()
def buy_credits(pack: str) -> dict:
	"""Somewhere to pay for a pack. The credit arrives by webhook, not here."""
	roles.require()
	return ask("onedesk.one_admin.proxy.buy_credits", pack=pack)


def _after(rows):
	"""Write the administrator's answer into the account, tell the other
	administrators what changed, and hand it back."""
	held = frappe.get_single("Workspace Account")
	before = [one.as_dict() for one in held.domains]
	_keep(held, rows)
	_tell_domains(before, rows, held.dns_target, but=frappe.session.user)
	return rows


def _plainly(refused) -> str:
	"""What the account said, without the exception's name in front of it."""
	import re

	return re.sub(r"^[\w.]+: ", "", str(refused.detail or refused)).strip()


def _seats_used() -> int:
	from onedesk.one.settings import seats_used

	return seats_used()


@frappe.whitelist()
def plans_offered() -> dict:
	"""The plans and add-ons this workspace could have, and what it has."""
	roles.require()
	return ask("onedesk.one_admin.proxy.plans_offered", seats_used=_seats_used())


@frappe.whitelist()
def plans_quote(needs: str | dict) -> dict:
	"""Every way to have this much in all, cheapest first (one_admin/plans.py)."""
	roles.require()
	return ask("onedesk.one_admin.proxy.plans_quote", needs=frappe.parse_json(needs) or {}, seats_used=_seats_used())


@frappe.whitelist(methods=["POST"])
def plans_take(plan: str, extras: str | dict | None = None, label: str | None = None) -> dict:
	"""Make the plan this, with exactly these add-ons, then ask the account
	again so the page draws what was bought. Every other administrator hears
	of it: it changes what the workspace pays."""
	roles.require()
	try:
		said = ask(
			"onedesk.one_admin.proxy.plans_take",
			plan=plan,
			extras=frappe.parse_json(extras) or {},
			seats_used=_seats_used(),
		)
	except faults.Refused as refused:
		frappe.throw(_plainly(refused), title=frappe._("The plan was not changed"))
	refresh()
	from onedesk.one import notify

	people = [one for one in _administrators() if one != frappe.session.user]
	if people:
		notify.notify(
			"Plan Changed",
			people,
			link=PAGE,
			by=frappe.utils.get_fullname(),
			plan=label or plan,
			monthly=frappe.utils.fmt_money(said.get("monthly") or 0, currency=said.get("currency") or "USD"),
		)
	return said


@frappe.whitelist(methods=["POST"])
def move_billing(email: str) -> dict:
	"""Make somebody else the one who pays: the workspace moves to the One
	account for their address (one_admin/accounts.py, move). Both addresses are
	mailed there; the other administrators hear it here."""
	roles.require()
	try:
		said = ask("onedesk.one_admin.proxy.billed_to", email=email, by=frappe.utils.get_fullname())
	except faults.Refused as refused:
		frappe.throw(_plainly(refused), title=frappe._("Who pays was not changed"))
	refresh()
	from onedesk.one import notify

	people = [one for one in _administrators() if one != frappe.session.user]
	if people:
		notify.notify(
			"Payer Changed",
			people,
			link=PAGE,
			by=frappe.utils.get_fullname(),
			email=said.get("billed_to") or email,
		)
	return said


@frappe.whitelist()
def domains() -> list:
	"""Every address this workspace answers at.

	Ours is first and is never removable. The rest are the customer's own, and
	each carries where press last said it got to.
	"""
	roles.require()
	return _after(_domains_ask("domain_list") or [])


@frappe.whitelist()
def domains_refresh() -> list:
	"""Go and ask, rather than draw what was last known.

	Check Again. A domain goes live minutes after it is added; the nightly
	refresh and the notice tell the administrators, and this is for somebody
	waiting on it.
	"""
	roles.require()
	rows = _after(_domains_ask("domain_refresh") or [])
	# And the rest of the account, so what the DNS points at is current too.
	refresh()
	return rows


@frappe.whitelist(methods=["POST"])
def domain_add(domain: str) -> dict:
	"""Add a name. It works once its CNAME points at the workspace's own
	address and Cloudflare has issued its certificate, usually minutes later;
	until then it waits, and the administrators are told when it works."""
	roles.require()
	answer = _domains_ask("domain_add", domain=domain) or {}
	_after(_domains_ask("domain_list") or [])
	return answer


@frappe.whitelist(methods=["POST"])
def domain_drop(domain: str) -> dict:
	roles.require()
	answer = _domains_ask("domain_drop", domain=domain) or {}
	_after(_domains_ask("domain_list") or [])
	return answer


@frappe.whitelist(methods=["POST"])
def domain_primary(domain: str) -> dict:
	"""Make one of them the address the workspace calls itself.

	This is the one that changes what the site believes rather than only what
	reaches it: press writes `host_name` into the site's config, so a link in an
	email starts using the new name. The other administrators hear of it.
	"""
	roles.require()
	answer = _domains_ask("domain_primary", domain=domain) or {}
	_after(_domains_ask("domain_list") or [])
	people = [one for one in _administrators() if one != frappe.session.user]
	if people:
		from onedesk.one import notify

		slots = {"by": frappe.utils.get_fullname(), "domain": answer.get("domain") or domain}
		notify.notify("Main Address Changed", people, link=DOMAINS, **slots)
		for email, lang in _addresses(people):
			notify.mail("Main Address Changed", email, lang=lang, **slots)
	return answer


def _domains_ask(what: str, **params):
	"""Ask the account about domains, and put its refusal (press's sentence,
	or ours) in front of the administrator as it was said."""
	try:
		return ask(f"onedesk.one_admin.proxy.{what}", **params)
	except faults.Refused as refused:
		frappe.throw(_plainly(refused), title=frappe._("Domains"))


#: The page the domain notices open.
DOMAINS = "/desk/workspace-settings?section=domains"

#: Press's word for a name that works.
WORKING = "Active"


def _tell_domains(before: list, after: list | None, target: str | None, but: str | None = None) -> None:
	"""Tell the administrators when one of the workspace's own names starts or
	stops working. A name removed on purpose is not one that stopped."""
	if not before or after is None:
		return
	was = {one.get("domain"): one.get("status") for one in before}
	if was != {one.get("domain"): one.get("status") for one in after}:
		# An open Domains page redraws (settings.js).
		for user in _administrators():
			frappe.publish_realtime("one_domains", {}, user=user, after_commit=True)
	people = [one for one in _administrators() if one != but]
	if not people:
		return
	from onedesk.one import notify

	for one in after:
		name, status = one.get("domain"), one.get("status")
		if one.get("given") or not name:
			continue
		if status == WORKING and was.get(name) != WORKING:
			slots = {"domain": name}
			notify.notify("Domain Working", people, link=DOMAINS, sender="Administrator", **slots)
			for email, lang in _addresses(people):
				notify.mail("Domain Working", email, lang=lang, **slots)
		elif name in was and was[name] == WORKING and status != WORKING:
			slots = {"domain": name, "target": target or ""}
			notify.notify("Domain Stopped Working", people, link=DOMAINS, sender="Administrator", **slots)
			for email, lang in _addresses(people):
				notify.mail("Domain Stopped Working", email, lang=lang, **slots)
