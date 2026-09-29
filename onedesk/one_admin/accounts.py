"""The One account: a person above their workspaces (docs/ONE-ACCOUNT.md).

An account is a frappe `User` on the admin site, of type Website User, named by
its email. It has no desk and no roles; it signs in at `/login` and sees only
the portal pages we give it. A workspace belongs to one through
`Tenant.account`. `owner_email` stays as what the workspace was bought with;
`account` is who holds it now.

Nothing here makes an account for somebody who has not paid: `hold` runs from
`signup.accept`, after the money, and from the patch for the workspaces that
were already there.
"""

import frappe
from frappe import _lt
from frappe.rate_limiter import rate_limit
from frappe.www import login

from onedesk.one_admin import house, site


def ensure(email: str) -> str | None:
	"""The account for this address, made if there is none.

	An address that is already a user is used as it is, whatever its type: an
	operator who buys a workspace holds it with the sign-in they already have.
	"""
	email = (email or "").strip().lower()
	if not email:
		return None
	found = frappe.db.get_value("User", {"name": email}) or frappe.db.get_value("User", {"email": email})
	if found:
		return found
	return (
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": email.split("@")[0],
				"user_type": "Website User",
				# Nothing is mailed for the account itself: the workspace's own
				# invitation is the mail that matters, and a second one saying
				# "you have an account" the same minute is noise.
				"send_welcome_email": 0,
			}
		)
		.insert(ignore_permissions=True)
		.name
	)


def hold(tenant: str, email: str) -> str | None:
	"""Put a workspace in the account for this address. Our own is in nobody's."""
	if not tenant or house.is_ours(tenant):
		return None
	account = ensure(email)
	if account:
		frappe.db.set_value("Tenant", tenant, "account", account)
	return account


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=login.get_login_with_email_link_ratelimit, seconds=60 * 60)
def send_login_link(email: str):
	"""Frappe's "Login with Email Link", on the admin site for accounts only.

	Overrides `frappe.www.login.send_login_link` (hooks). Anywhere but the admin
	site it is frappe's, untouched. Here the link is made by frappe
	(`_generate_temporary_login_link`, spent by `login_via_key`), and only for a
	Website User: an operator keeps their password and passkey, and a mailed
	link is not a door into the console. Every other address gets the same
	silent answer an unknown one does, so the page tells nobody who has what.
	The mail is ours (Sign-in Link), in the same words as every other.
	"""
	if not site.is_admin():
		return login.send_login_link(email)
	if not frappe.get_system_settings("login_with_email_link"):
		return
	email = (email or "").strip().lower()
	if frappe.db.get_value("User", {"name": email, "enabled": 1}, "user_type") != "Website User":
		return
	from onedesk.one import notify

	minutes = frappe.get_system_settings("login_with_email_link_expiry") or 10
	notify.mail(
		"Sign-in Link",
		email,
		link=login._generate_temporary_login_link(email, minutes),
		minutes=minutes,
		now=True,
	)


def home_page(user: str) -> str | None:
	"""Where an account lands after signing in (hooks: get_website_user_home_page).

	On the admin site, its own page rather than frappe's /portal, whose menu is
	ERPNext's customer portal. Anywhere else, what it would have been.
	"""
	if site.is_admin():
		return "account"
	named = frappe.get_hooks("website_user_home_page")
	return named[-1] if named else None


def workspaces(user: str) -> list[dict]:
	"""The workspaces this account holds, each with where it stands, for its
	own page. A dropped one is gone and is not listed."""
	held = frappe.get_all(
		"Tenant",
		filters={"account": user, "is_house": 0, "status": ["!=", "Dropped"]},
		fields=[
			"name",
			"workspace_name",
			"domain",
			"primary_domain",
			"status",
			"status_since",
			"offering",
			"live_on",
			"creation",
			"stripe_customer",
		],
		order_by="creation asc",
	)
	told = [{**one, **_stands(one)} for one in held]
	# What owes money first: it is the one thing on the page with a clock.
	return sorted(told, key=lambda one: not one["owing"])


#: What a customer reads for each rung: the pill, its colour, and whether the
#: workspace can be opened. Words a customer would use, not the ladder's.
STANDS = {
	"Requested": (_lt("Being built"), "gray", False),
	"Provisioning": (_lt("Being built"), "gray", False),
	"Live": (_lt("Live"), "green", True),
	"Overdue": (_lt("Payment overdue"), "orange", True),
	"Suspended": (_lt("Suspended"), "red", False),
	"Archived": (_lt("Archived"), "red", False),
	"Failed": (_lt("Not built yet"), "red", False),
}

#: The sentence under an owing workspace: what happens next, and when.
FALLS = {
	"Overdue": _lt("Pay within {0} days, or it is suspended."),
	"Suspended": _lt("Pay within {0} days, or it is archived."),
	"Archived": _lt("Pay within {0} days, or it is closed for good."),
}


def _stands(one) -> dict:
	"""Where one workspace stands, in the account's words (lifecycle.standing
	for the clock, so the days here are the days the ladder will walk)."""
	from frappe.utils import add_days, formatdate, getdate, today

	from onedesk.one_admin import lifecycle

	pill, tone, opens = STANDS.get(one.status, (_lt("Closed"), "gray", False))
	plan = (
		frappe.db.get_value("Offering", one.offering, ["label", "trial_days"], as_dict=True)
		if one.offering
		else None
	)
	line = plan.label if plan else ""
	if one.status == "Live" and plan and plan.trial_days:
		ends = add_days(getdate(one.live_on or one.creation), plan.trial_days)
		if ends >= getdate(today()):
			pill, tone = _lt("On trial"), "blue"
			line = frappe._("{0}, free until {1}").format(plan.label, formatdate(ends))
	owing = one.status in FALLS
	if owing:
		left = lifecycle.standing(one).get("days_left")
		line = (
			str(FALLS[one.status]).format(left) if left is not None else frappe._("Pay to keep it running.")
		)
	elif one.status in ("Requested", "Provisioning"):
		line = frappe._("This takes a few minutes. We will mail you when it is ready.")
	elif one.status == "Failed":
		line = frappe._("Setting it up hit a problem on our side, and we are on it.")
	return {
		"at": one.primary_domain or one.domain,
		"pill": str(pill),
		"tone": tone,
		"line": line,
		"opens": opens,
		"owing": owing,
		"may_pay": owing and bool(one.stripe_customer),
	}


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=10, seconds=60)
def pay(tenant: str) -> dict:
	"""Stripe's billing portal for a workspace this account holds: its open
	invoice, its card. Back to /account after."""
	if not site.is_admin() or frappe.session.user == "Guest":
		frappe.throw(frappe._("Sign in to your One account first."), frappe.PermissionError)
	if frappe.db.get_value("Tenant", tenant, "account") != frappe.session.user:
		frappe.throw(frappe._("This workspace is not in your account."), frappe.PermissionError)
	from onedesk.one_admin import billing

	return {"url": billing.portal(tenant, frappe.utils.get_url("/account"))}
