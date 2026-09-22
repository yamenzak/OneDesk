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

	try:
		tenant = _tenant_for(asked)
	except Exception as raised:
		asked.db_set({"status": "Failed", "failed_reason": str(raised)[:500]})
		raise

	asked.db_set({"tenant": tenant, "status": "Provisioning", "failed_reason": None})
	runner.start(tenant)
	return tenant


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


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=STARTS_A_MINUTE, seconds=A_MINUTE)
def available(name: str) -> dict:
	"""What the signup page asks while somebody is still typing."""
	site.require_admin()
	return free(name)


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=STARTS_A_MINUTE, seconds=A_MINUTE)
def start(email: str, workspace_name: str, offering: str, jurisdiction: str = "Global") -> dict:
	"""Take a signup and hand back somewhere to pay.

	The request is written before the customer is sent to Stripe, so a payment
	that completes always has something to attach itself to. The reverse — a
	session created first — leaves a paid customer whose request never existed.
	"""
	site.require_admin()
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

	from onedesk.one_admin import stripe

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
