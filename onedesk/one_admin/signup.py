"""Turning somebody who asked into a workspace that exists.

Two rules, and the second is the one that matters.

**Nothing is provisioned until money has moved.** A request sits as `New` until
the payment says otherwise, and `accept` is what the payment calls.

**Nothing unwinds.** `accept` runs after a charge, so the policy is never to
leave a customer with a receipt and nothing to show for it. Each part records
where it got to, a failure marks the request failed with a reason an operator can
read, and the resume is the same call again — which is why every part of it is
safe to run twice. Unwinding is how you end up having taken money and then
deleted the thing it bought.
"""

import frappe
from frappe.rate_limiter import rate_limit

from onedesk.one_admin import keys, runner, site

#: The statuses a slug is still spoken for in. An abandoned request lets its
#: name go; one being paid for does not.
HOLDING = ("New", "Paying", "Paid", "Provisioning", "Done")

#: Days a request may sit unpaid before it is Abandoned and its name is free
#: again. The same days sales.abandoned loses its deal after.
ABANDONED_DAYS = 7


def tidy_slug(raw: str) -> str:
	try:
		return keys.slug(raw)
	except keys.Unnameable as raised:
		frappe.throw(str(raised), frappe.ValidationError)


def refuse_a_taken_slug(slug: str) -> None:
	"""A name is somebody's the moment they ask for it.

	Checked against live workspaces and against requests still in flight, so two
	people signing up at once do not both get told yes.
	"""
	if frappe.db.exists("Tenant", slug):
		frappe.throw(frappe._("{0} is taken.").format(slug), frappe.DuplicateEntryError)
	if frappe.db.exists("Account Request", {"slug": slug, "status": ["in", HOLDING]}):
		frappe.throw(frappe._("{0} is taken.").format(slug), frappe.DuplicateEntryError)


def free(raw: str) -> dict:
	"""What the signup page asks while somebody is typing."""
	try:
		slug = keys.slug(raw)
	except keys.Unnameable as raised:
		return {"free": False, "slug": None, "why": str(raised)}
	try:
		refuse_a_taken_slug(slug)
	except frappe.DuplicateEntryError:
		return {"free": False, "slug": slug, "why": frappe._("{0} is taken.").format(slug)}
	return {"free": True, "slug": slug, "why": None}


def accept(request: str) -> str:
	"""The money landed. Make the workspace.

	Idempotent in the way that counts: a request that already has a tenant
	returns it rather than making a second one, because the caller is a webhook
	and a webhook is delivered more than once.
	"""
	site.require_admin()
	asked = frappe.get_doc("Account Request", request)
	if asked.tenant:
		return asked.tenant

	# Money was taken: the operator is told, and told again if it is not built.
	from onedesk.one_admin import tell

	was = asked.status
	if was in ("New", "Paying", "Abandoned"):
		asked.db_set("status", "Paid", notify=True)
		tell.signup_paid(asked)
	try:
		if was == "Abandoned":
			# Paid after its name was let go: somebody else may have it now,
			# and _tenant_for would hand them this customer's money.
			_still_free(asked)
		tenant = _tenant_for(asked)
	except Exception as raised:
		asked.db_set({"status": "Failed", "failed_reason": str(raised)[:500]}, notify=True)
		tell.signup_not_built(asked, str(raised))
		raise

	asked.db_set({"tenant": tenant, "status": "Provisioning", "failed_reason": None}, notify=True)
	# Paid for, so theirs: into the account for the address it was bought with.
	from onedesk.one_admin import accounts

	accounts.hold(tenant, asked.email)
	runner.start(tenant)
	return tenant


def _still_free(asked) -> None:
	if frappe.db.exists("Tenant", asked.slug) or frappe.db.exists(
		"Account Request", {"slug": asked.slug, "status": ["in", HOLDING], "name": ["!=", asked.name]}
	):
		frappe.throw(
			frappe._("{0} was taken by somebody else after this signup was abandoned.").format(asked.slug)
		)


def built(tenant) -> None:
	"""The workspace a signup paid for is live (steps.live)."""
	for name in frappe.get_all(
		"Account Request",
		filters={"tenant": tenant.name, "status": ["in", ["Paid", "Provisioning", "Failed"]]},
		pluck="name",
	):
		frappe.get_doc("Account Request", name).db_set({"status": "Done", "failed_reason": None}, notify=True)


def abandon() -> None:
	"""Nightly: a request nobody paid for in a week is Abandoned, which lets
	its name go. A payment that still arrives is taken (accept)."""
	if not site.is_admin():
		return
	from frappe.utils import add_days, now_datetime

	for name in frappe.get_all(
		"Account Request",
		filters={
			"status": ["in", ["New", "Paying"]],
			"tenant": ["is", "not set"],
			"creation": ["<", add_days(now_datetime(), -ABANDONED_DAYS)],
		},
		pluck="name",
	):
		frappe.db.set_value("Account Request", name, "status", "Abandoned", update_modified=False)
	frappe.db.commit()


def _tenant_for(asked) -> str:
	"""The workspace record, with what it was sold written onto it.

	The quotas are copied rather than looked up through the offering, because an
	offering is a price list somebody edits and a tenant is what a customer
	bought. Re-pricing a plan must not silently change what an existing customer
	is allowed.
	"""
	if frappe.db.exists("Tenant", asked.slug):
		return asked.slug

	sold = frappe.get_cached_doc("Offering", asked.offering)
	frappe.get_doc(
		{
			"doctype": "Tenant",
			"slug": asked.slug,
			"workspace_name": asked.workspace_name,
			"owner_email": asked.email,
			"status": "Requested",
			"offering": asked.offering,
			"jurisdiction": asked.jurisdiction,
			"cluster": asked.cluster,
			"country": asked.country,
			"bench": _bench_for(asked.cluster),
			# Decimal gigabytes, not binary. The plan says 25 GB, R2 bills in
			# decimal, and every tool a customer checks with reports decimal —
			# so 1024³ quietly gave them 26.8 GB and made the screen say 27 for
			# a plan called 25. Found by putting a progress bar next to it.
			"storage_limit": (sold.storage_gb or 0) * 1000 * 1000 * 1000,
			"database_limit": (sold.database_gb or 0) * 1000 * 1000 * 1000,
			"seats": sold.seats or 0,
			"credits_a_month": sold.credits_a_month or 0,
		}
	).insert(ignore_permissions=True)
	return asked.slug


def _bench_for(cluster: str | None) -> str:
	"""The bench group a site for this cluster goes on.

	Asked of press rather than kept in a table. With one bench it is the one
	there is; the day there are several this is where the choosing goes.
	"""
	from onedesk.one_admin import press

	benches = press.benches()
	if not benches:
		frappe.throw(frappe._("Frappe Cloud has no bench group to place a site on."))
	return benches[0].get("name")


#: Signups a minute from one address. A person filling in a form makes one; a
#: script making twenty is taking names nobody will use.
A_MINUTE = 60
STARTS_A_MINUTE = 5

#: Name checks a minute. The page asks after every pause in the typing, and five
#: was measured running out on one name typed in bursts, which froze the hint.
CHECKS_A_MINUTE = 30

#: Days after an unpaid signup before its one reminder goes (remind).
REMIND_AFTER_DAYS = 1


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=CHECKS_A_MINUTE, seconds=A_MINUTE)
def available(name: str) -> dict:
	"""What the signup page asks while somebody is still typing."""
	site.require_admin()
	return free(name)


#: Minutes a build may take before the welcome page stops saying "a few".
SLOW_MINUTES = 15


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=CHECKS_A_MINUTE, seconds=A_MINUTE)
def state(request: str, key: str) -> dict:
	"""Where a signup stands, for the welcome page to look again without
	reloading. The key or nothing, as the page itself (owned)."""
	site.require_admin()
	asked = owned(request, key)
	if not asked:
		return {"status": None}
	return {"status": asked.status, "slow": slow(asked)}


def slow(asked) -> bool:
	"""Being built for longer than a build takes: the page says so honestly."""
	if asked.status not in ("Paid", "Provisioning"):
		return False
	from frappe.utils import now_datetime, time_diff_in_seconds

	return time_diff_in_seconds(now_datetime(), asked.modified) > SLOW_MINUTES * 60


def owned(request: str, key: str):
	"""The request, if the key is the one it was given, else None.

	The key is what the welcome page and the reminder carry. Without it a
	request's name, which counts up, would open anybody's signup: their
	workspace's name and their email address.
	"""
	import secrets

	if not request or not key:
		return None
	held = frappe.db.get_value("Account Request", request, "access_key")
	if not held or not secrets.compare_digest(held, key):
		return None
	return frappe.get_doc("Account Request", request)


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=STARTS_A_MINUTE, seconds=A_MINUTE)
def pay(request: str, key: str) -> dict:
	"""A fresh checkout for a signup somebody left before paying.

	Stripe's own page lasts a day, so the reminder cannot link to it; it links
	to the welcome page, which asks for a new one here.
	"""
	site.require_admin()
	asked = owned(request, key)
	if not asked or asked.status not in ("New", "Paying") or asked.tenant:
		frappe.throw(frappe._("This signup can no longer be paid for. Start again."))
	if not frappe.db.get_value("Offering", asked.offering, "enabled"):
		frappe.throw(frappe._("That plan is no longer on offer. Start again."))
	from onedesk.one_admin import stripe

	return {"pay_at": stripe.checkout(asked.name)}


def let_go(asked) -> None:
	"""Somebody closed the payment page: the name is theirs to ask for again.

	Abandoned at once rather than after a week, because "Start again" is the
	link they are given, and a name still held by their own request answers
	"taken" to them. A payment that arrives anyway is still taken (accept).
	"""
	if asked.status in ("New", "Paying") and not asked.tenant:
		asked.db_set("status", "Abandoned", notify=True)


def remind() -> None:
	"""Daily: one mail to somebody who filled the form and never paid.

	Once, a day after, and never for a request that is Abandoned. The link is
	the welcome page with the request's key, which offers a fresh checkout.
	"""
	if not site.is_admin():
		return
	from frappe.utils import add_days, get_url, now_datetime

	from onedesk.one import notify

	for asked in frappe.get_all(
		"Account Request",
		filters={
			"status": ["in", ["New", "Paying"]],
			"tenant": ["is", "not set"],
			"reminded_on": ["is", "not set"],
			"creation": ["<", add_days(now_datetime(), -REMIND_AFTER_DAYS)],
		},
		fields=["name", "email", "workspace_name", "slug", "access_key"],
	):
		if not asked.email or not asked.access_key:
			continue
		notify.mail(
			"Finish Signing Up",
			asked.email,
			workspace=asked.workspace_name or asked.slug,
			link=f"{get_url()}/welcome?request={asked.name}&key={asked.access_key}",
			reference_doctype="Account Request",
			reference_name=asked.name,
		)
		frappe.db.set_value(
			"Account Request", asked.name, "reminded_on", now_datetime(), update_modified=False
		)
	frappe.db.commit()


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=STARTS_A_MINUTE, seconds=A_MINUTE)
def start(workspace_name: str, offering: str, jurisdiction: str = "Global", email: str | None = None) -> dict:
	"""Take a signup and hand back somewhere to pay.

	The request is written before the customer is sent to Stripe, so a payment
	that completes always has something to attach itself to. The reverse — a
	session created first — leaves a paid customer whose request never existed.

	Somebody signed in to their One account signs up as that account: the
	email is theirs, whatever the form sent, so the workspace joins the account
	they are looking at (accounts.hold, at payment).
	"""
	site.require_admin()
	if frappe.session.user != "Guest":
		email = frappe.db.get_value("User", frappe.session.user, "email") or frappe.session.user
	if not email:
		frappe.throw(frappe._("An email address is needed."))
	sold = frappe.db.get_value("Offering", offering, ["name", "enabled"], as_dict=True)
	if not sold or not sold.enabled:
		frappe.throw(frappe._("That is not something on offer."))

	asked = frappe.get_doc(
		{
			"doctype": "Account Request",
			"email": email,
			"workspace_name": workspace_name,
			"slug": workspace_name,
			"offering": sold.name,
			"jurisdiction": jurisdiction if jurisdiction in ("Global", "EU") else "Global",
			"cluster": _one_cluster(),
			"status": "New",
		}
	).insert(ignore_permissions=True)

	from onedesk.one_admin import sales, stripe

	# Our own lead and deal for it, before the customer leaves to pay (sales.py).
	sales.signed_up(asked.name)
	return {"request": asked.name, "pay_at": stripe.checkout(asked.name)}


def _one_cluster() -> str | None:
	"""Where a workspace goes when there is nowhere else for it to go.

	With one cluster the signup page asks nothing — a picker with one option is
	a question with one answer. The day there are several, this is replaced by
	what the customer chose.
	"""
	from onedesk.one_admin import press

	found = press.clusters(_bench_for(None))
	return found[0].get("name") if found else None
