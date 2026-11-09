"""What OneAI does in OneAdmin: says what needs the operator, and why, and
how one workspace is doing.

The operator's own readers, on the admin site only and for One Operator only.
"""

from typing import Annotated

import frappe
from frappe import _lt

from onedesk.one_admin import ledger

NOT_FOR_AI = {
	"accounts.pay": "A payment is made by the account holder on Stripe's own page.",
	"accounts.card": "A card is changed by the account holder on Stripe's own page.",
	"accounts.save_name": "An account holder changes their own name on their account page, where OneAI isn't.",
	"accounts.ask_email_change": "An account's address decides who may sign in to it, so its holder changes it by hand.",
	"control.save": "OneAdmin's keys and prices are saved by the operator changing them.",
	"operator.order_server": "A server costs money from the moment it is ordered, so an operator presses it.",
	"operator.rebuild": "Building a workspace again from a backup is an operator's call, made on the workspace.",
	"operator.roll_back": "Putting a workspace back to a backup loses its newer work, so an operator presses it.",
	"operator.move": "Moving a workspace takes it offline for the move, so an operator presses it.",
	"operator.run_now": "Running a job's next step early is an operator's call on a job they are looking at.",
	"private.new_code": "A code is shown once, to the operator who asked for it.",
	"setup.set_up": "Set Up Cloudflare uses the master key and changes the account, so an operator presses it.",
	"site.make_operator": "Who may run OneAdmin is decided by an operator by hand.",
	"accounts.send_login_link": "A sign-in link is asked for on the sign-in page, by somebody not signed in yet.",
	"proxy.billed_to": "A workspace's own server calls this with its token, when a person there asks.",
	"proxy.close": "A workspace's own server calls this with its token, when a person there asks.",
	"proxy.mail_send": "A workspace's own server calls this with its token, when a person there asks.",
	"proxy.office_convert": "A workspace's own server calls this with its token, when a person there asks.",
	"proxy.set_auto_topup": "A workspace's own server calls this with its token, when a person there asks.",
	"proxy.spend_limit": "A workspace's own server calls this with its token, when a person there asks.",
	"proxy.update_now": "A workspace's own server calls this with its token, when a person there asks.",
	"proxy.update_window": "A workspace's own server calls this with its token, when a person there asks.",
	"proxy.withdraw_closing": "A workspace's own server calls this with its token, when a person there asks.",
	"servers.pressure": "A server reports this about itself, and no person is there.",
	"servers.reported": "A server reports this about itself, and no person is there.",
	"signup.pay": "Paying is done by whoever is signing up, on the signup page.",
	"signup.start": "A signup is started by whoever is signing up, on the signup page.",
	"stripe.webhook": "Stripe calls this, and no person is there.",
	"aws.link": "Connecting AWS is done by an operator signed in to that account.",
	"cloudflare_signin.start": "Signing in to Cloudflare is done by an operator in their own browser.",
	"operator.connect_server": "A connected machine runs the command on itself, so an operator asks for it.",
	"proxy.copies_agreed": "A workspace's own server calls this with its token, and no person is there.",
	"proxy.errors_seen": "A workspace's own server calls this with its token, and no person is there.",
	"sessions.delete": "Deleting a session loses what was done on it, so an operator presses it.",
	"sessions.resume": "A session is started again by the operator using it.",
	"sessions.sign_in": "A sign-in link is for the operator who pressed it.",
	"sessions.start": "A session uses a server and can hold a copy of a workspace, so an operator starts it.",
	"sessions.stop": "A session is stopped by the operator using it.",
}

SUGGESTIONS = {
	"workspace:One Admin": [
		{
			"label": _lt("What needs me today?"),
			"ask": _lt(
				"What needs me in OneAdmin today? Say what is most urgent first, why each one is stuck, and what I should do about it."
			),
			"expects": "console_today",
		},
	],
	"Tenant": [
		{
			"label": _lt("How is this workspace doing?"),
			"ask": _lt(
				"How is this workspace doing? Say where it stands and whether anything is wrong: its payments, "
				"storage, credits, domains and its last jobs, and what I should do about anything that is."
			),
			"can": "read",
			"view": "Form",
			"expects": "workspace_facts",
		},
	],
	"Tenant Domain": [
		{
			"label": _lt("Why isn't this domain working?"),
			"ask": _lt(
				"Why isn't this domain working? Say what Cloudflare says is wrong in plain words, what the customer "
				"has to change in their DNS, and whether anything is ours to fix."
			),
			"can": "read",
			"view": "Form",
			"when": {"status": ["Pending", "Broken", "Gone"]},
			"expects": "workspace_facts",
		},
	],
	"Offering": [
		{
			"label": _lt("How do our plans compare?"),
			"ask": _lt(
				"How do our plans compare? Go through the price list: what each plan costs and gives, where the steps "
				"between plans are uneven, and whether the add-ons and packs are priced in line with them."
			),
			"can": "read",
			"view": "List",
			"expects": "price_list",
		},
		{
			"label": _lt("Who has this?"),
			"ask": _lt("Which workspaces have this, how many are live, and what do they pay?"),
			"can": "read",
			"view": "Form",
			"when": {"kind": ["Plan", "Add-on"]},
			"expects": "price_list",
		},
	],
	"report:Price Check": [
		{
			"label": _lt("What should we change?"),
			"ask": _lt(
				"Look at the price check: what is wrong and what is close, with the numbers. Say what to change "
				"first, and by how much, to make the price list hold."
			),
			"expects": "run_report",
		},
	],
	"report:Plan Calculator": [
		{
			"label": _lt("What should they buy?"),
			"ask": _lt(
				"Ask me what they need, or which workspace, if I have not said. Then say the cheapest plan and "
				"add-ons for it, what it costs a month, and the next best way."
			),
			"expects": "plan_quote",
		},
	],
	"Provisioning Job": [
		{
			"label": _lt("Why did this job fail?"),
			"ask": _lt(
				"Why did this job fail? Say where it stopped, what the error means in plain words, and whether resuming it is likely to work."
			),
			"can": "read",
			"view": "Form",
			"when": {"status": ["Failed"]},
			"expects": "job_facts",
		},
		{
			"label": _lt("Why is this job waiting?"),
			"ask": _lt(
				"Why is this job waiting? Say which step it is on, what it is waiting for, how many times it has tried, and whether anything is wrong."
			),
			"can": "read",
			"view": "Form",
			"when": {"status": ["Pending", "Waiting"]},
			"expects": "job_facts",
		},
	],
	"One Admin Settings": [
		{
			"label": _lt("Is everything set up?"),
			"ask": _lt(
				"Is everything OneAdmin runs on set up? Say which connections are missing and what each stops, "
				"what Set Up Cloudflare last said, and whether the money settings look sensible."
			),
			"can": "read",
			"view": "Form",
			"expects": "settings_check",
		},
	],
	"report:AI Usage": [
		{
			"label": _lt("Who is spending the most?"),
			"ask": _lt(
				"Who is spending the most on OneAI this month, on which models and for which actions? Say what it "
				"was charged, what it cost us and the margin, and anything that looks wrong."
			),
			"expects": "run_report",
		},
	],
	ledger.ENTRY: [
		{
			"label": _lt("Where did the credits go?"),
			"ask": _lt(
				"Where did this workspace's OneCredits go? Say what it has left and until when, what it spent "
				"this month and on which models, and anything given or taken back by hand, with its note."
			),
			"can": "read",
			"view": "Form",
			"expects": "credit_facts",
		},
	],
	"Account Request": [
		{
			"label": _lt("Why wasn't this built?"),
			"ask": _lt(
				"Why wasn't this signup's workspace built? Say what stopped it in plain words, whether Build "
				"Workspace is likely to work now, and what to do if it is not."
			),
			"can": "read",
			"view": "Form",
			"when": {"status": ["Failed", "Paid"]},
			"expects": "signup_facts",
		},
	],
}


def page(said: dict) -> str | None:
	"""The sentence the model is told on OneAdmin's Home, Servers, Billing, Releases, Status and Sessions."""
	if said.get("page") == "oneadmin-servers":
		return "The reader is an operator of One, on OneAdmin's Servers: every server as a card with its status, live CPU, memory and disk, workspaces and release, and below them the requests, Workers and R2 storage Cloudflare counted over the last day."
	if said.get("page") == "oneadmin-billing":
		return (
			"The reader is an operator of One, on OneAdmin's Billing: what live workspaces pay a month, what that leaves "
			"against the margin floor, OneCredits sold and used, OneAI's cost, and how the plans split. run_report reads AI Usage and Price Check."
		)
	if said.get("page") == "oneadmin-releases":
		return (
			"The reader is an operator of One, on OneAdmin's Releases: each release, the version each server holds, and "
			"each workspace's window. A workspace waiting on new terms waits 30 days and then moves. How updates work is in OneAdmin's documentation (how_to)."
		)
	if said.get("page") == "oneadmin-status":
		return (
			"The reader is an operator of One, on OneAdmin's Status: whether each service One depends on is "
			"working now, the share of its checks that failed each day for 30 days, and what failed. Nothing is "
			"changed from this screen. How the console works is in OneAdmin's documentation (how_to)."
		)
	if said.get("page") == "oneadmin-sessions":
		return "The reader is an operator of One, on OneAdmin's Sessions: every session with its state, where it started from, its link and when it expires."
	if said.get("page") != "oneadmin":
		return None
	return (
		"The reader is an operator of One, on OneAdmin's Home: how many workspaces are live, being built, "
		"owing, failed, or paid for and not built, and a list of what needs them. console_today reads that "
		"list with each item's reason. Nothing is changed from the panel: Resume, Build Workspace and Check Again "
		"are buttons on Home. How the console works is in OneAdmin's documentation (how_to)."
	)


def _operator() -> bool:
	from onedesk.one_admin import site

	return site.is_admin() and site.OPERATOR in frappe.get_roles()


def console_today() -> dict:
	"""For an operator of One only: what needs them in OneAdmin, as Home lists
	it. Jobs that failed with their step and error, workspaces paid for and not
	built, workspaces owing and since when, and domains not working or waiting
	for their DNS; and how many workspaces are live and being built."""
	from onedesk.one_admin import home, site

	if not site.is_admin() or site.OPERATOR not in frappe.get_roles():
		return {"error": "Only an operator of One, on the admin site, sees the console."}
	return {
		"counts": {one["key"]: one["value"] for one in home.counts()},
		"needs": [
			{key: one.get(key) for key in ("kind", "doctype", "name", "title", "why", "detail", "since")}
			for one in home.needs()
		],
	}


DOMAIN_STATUS = {
	"Pending": "Waiting",
	"Active": "Working",
	"Broken": "Not working",
	"Gone": "Not at Cloudflare",
}


def workspace_facts(
	workspace: Annotated[
		str, "The workspace's id, its slug, as the page names it; or one of its domains, such as crm.acme.com."
	],
) -> dict:
	"""For an operator of One only: how one workspace stands. Its status and
	since when, whether it owes and when it falls a rung, its plan and
	add-ons, storage, OneCredits and this month's spend, its last jobs and
	log entries, and each domain: whether it works, what Cloudflare says
	stops it, where its CNAME must point, whether it is the main address and
	since when it has waited. Given a domain, the workspace it belongs to."""
	if not _operator():
		return {"error": "Only an operator of One, on the admin site, sees a workspace."}
	if not frappe.db.exists("Tenant", workspace) and frappe.db.exists("Tenant Domain", workspace):
		workspace = frappe.db.get_value("Tenant Domain", workspace, "tenant")
	if not workspace or not frappe.db.exists("Tenant", workspace):
		return {"error": f"There is no workspace {workspace}. Ask which one they meant."}
	from onedesk.one_account.heads import size
	from onedesk.one_admin import operator

	held = frappe.get_doc("Tenant", workspace)
	where = operator.standing(held.name)
	credits = operator.credit_standing(held.name)
	return {
		"workspace": held.workspace_name,
		"owner": held.owner_email,
		"status": held.status,
		"since": str(held.status_since) if held.status_since else None,
		"owing": bool(where.get("owing")),
		"falls_to": where.get("next") if where.get("days_left") is not None else None,
		"days_left": where.get("days_left"),
		"plan": frappe.db.get_value("Offering", held.offering, "label") if held.offering else None,
		"add_ons": [
			{
				"add_on": frappe.db.get_value("Offering", one.offering, "label") or one.offering,
				"quantity": one.quantity,
			}
			for one in held.get("add_ons") or []
		],
		"address": held.domain or held.site,
		"storage": size(held.storage_bytes),
		"storage_limit": size(held.storage_limit) if held.storage_limit else None,
		"database": size(held.database_bytes),
		"database_limit": size(held.database_limit) if held.database_limit else None,
		"credits_left": credits.get("available"),
		"credits_a_month": held.credits_a_month,
		"credits_this_month": credits.get("month_credits"),
		"calls_this_month": credits.get("month_calls"),
		"domains": [
			{
				"domain": one.domain,
				"status": DOMAIN_STATUS.get(one.status, one.status),
				"problem": one.problem,
				"cname_to": held.domain,
				"main_address": bool(one.is_main),
				"asked_on": str(one.asked_on) if one.asked_on else None,
				"last_asked": str(one.modified),
			}
			for one in frappe.get_all(
				"Tenant Domain",
				filters={"tenant": held.name},
				fields=["domain", "status", "problem", "is_main", "asked_on", "modified"],
			)
		],
		"domains_checked": "Cloudflare checks by itself; One asks it each night until the name works, and Check "
		"Again asks now.",
		"jobs": frappe.get_all(
			"Provisioning Job",
			filters={"tenant": held.name},
			fields=["name", "kind", "status", "step", "error", "modified"],
			order_by="modified desc",
			limit=5,
		),
		"log": frappe.get_all(
			"Tenant Event",
			filters={"tenant": held.name},
			fields=["kind", "detail", "creation"],
			order_by="creation desc",
			limit=10,
		),
	}


def job_facts(
	job: Annotated[str, "The job's id, as the page names it, such as PROV-26-00012."],
) -> dict:
	"""For an operator of One only: one job, as its form shows it. What it is
	doing to which workspace, every step of its walk in words with the ones
	done, the step it is on, how many times it has tried it and when it runs
	next, the error it stopped with, and where the workspace stands now."""
	if not _operator():
		return {"error": "Only an operator of One, on the admin site, sees a job."}
	if not frappe.db.exists("Provisioning Job", job):
		return {"error": f"There is no job {job}. Ask which one they meant."}
	from onedesk.one_admin import operator, runner

	held = frappe.get_doc("Provisioning Job", job)
	walk = operator.walk(job)
	return {
		"job": held.name,
		"kind": held.kind,
		"status": held.status,
		"workspace": frappe.db.get_value("Tenant", held.tenant, "workspace_name") or held.tenant,
		"workspace_status": frappe.db.get_value("Tenant", held.tenant, "status"),
		"steps": [{"step": one["said"], "done": one["done"]} for one in walk["steps"]],
		"on_step": walk["at"] + 1 if walk["at"] < walk["of"] else None,
		"of": walk["of"],
		"attempts": held.attempts,
		"next_run": str(held.next_run_at) if held.next_run_at else None,
		"finished": str(held.finished_at) if held.finished_at else None,
		"error": held.error,
		"started": str(held.creation),
		"last_moved": str(held.modified),
		"gives_up_after": runner.GIVE_UP_AFTER,
	}


def settings_check() -> dict:
	"""For an operator of One only: which of OneAdmin's connections are filled
	in and what each missing one stops, what Set Up Cloudflare last said, and
	the money settings. A key is only ever said to be set or not."""
	if not _operator():
		return {"error": "Only an operator of One, on the admin site, sees the settings."}
	import json

	from onedesk.one_admin import price_list, heads, offerings

	held = frappe.get_single("One Admin Settings")
	try:
		setup = json.loads(held.cloudflare_setup or "[]")
	except ValueError:
		setup = []
	return {
		"missing": heads.settings_missing(held),
		"cloudflare_setup": [{key: one.get(key) for key in ("step", "state", "detail")} for one in setup],
		"money": {
			"credits_per_dollar_of_provider_cost": price_list.credits_per_dollar(),
			"markup": price_list.MARKUP,
			"a_credit_sells_for": round(offerings.credit_price(), 5),
			"margin_floor": price_list.MARGIN_FLOOR,
			"currency": price_list.CURRENCY,
		},
		"grace_days": {"overdue": held.grace_days, "suspended": held.held_days, "archived": held.kept_days},
		"workspace_domain": held.tenant_domain,
		"mail_domain": held.mail_domain,
	}


def credit_facts(
	workspace: Annotated[str, "The workspace's id, its slug, as the page names it."],
) -> dict:
	"""For an operator of One only: a workspace's OneCredits. What it has
	and what is promised to calls in flight, each grant with what is left of
	it and until when, this month's spend by model, and the credits given or
	taken back by hand with their notes."""
	if not _operator():
		return {"error": "Only an operator of One, on the admin site, sees a workspace's credits."}
	if not frappe.db.exists("Tenant", workspace):
		return {"error": f"There is no workspace {workspace}. Ask which one they meant."}
	from frappe.utils import add_days, get_first_day, getdate

	return {
		"standing": ledger.standing(workspace),
		"grants": [
			{
				"entry": one["name"],
				"credits": one["credits"],
				"left": one["left"],
				"from": one["source"],
				"note": one["why"],
				"expires_on": str(one["expires_on"]) if one["expires_on"] else None,
				"given_on": str(one["creation"].date()),
			}
			for one in ledger.grants(workspace)
		],
		"this_month_by_model": [
			{"model": row.why, "calls": row.calls, "credits": round(row.credits or 0, 2)}
			for row in ledger.usage(
				get_first_day(getdate()), add_days(getdate(), 1), ["why"], tenant=workspace
			)
		],
		"taken_back": ledger.taken(workspace),
	}


def signup_facts(
	signup: Annotated[str, "The signup's id, as the page names it, such as REQ-26-00015."],
) -> dict:
	"""For an operator of One only: one signup. Who asked for which workspace
	on which plan, where it stands in words, why making it stopped, whether
	its name is still free for Build Workspace, what Stripe told us of its
	payment, and its workspace and last job if it has one."""
	if not _operator():
		return {"error": "Only an operator of One, on the admin site, sees a signup."}
	if not frappe.db.exists("Account Request", signup):
		return {"error": f"There is no signup {signup}. Ask which one they meant."}
	from onedesk.one_admin import heads

	held = frappe.get_doc("Account Request", signup)
	taken = frappe.db.exists("Tenant", held.slug) and held.tenant != held.slug
	said = {
		"signup": held.name,
		"email": held.email,
		"workspace_name": held.workspace_name,
		"address": held.slug,
		"plan": frappe.db.get_value("Offering", held.offering, "label") or held.offering,
		"status": str(heads.REQUEST.get(held.status, (None, held.status))[1]),
		"why_it_stopped": held.failed_reason,
		"asked_on": str(held.creation),
		"name_taken_by_another_workspace": bool(taken),
		"build_workspace_offered": not held.tenant and held.status in ("Paid", "Failed"),
		"stripe": frappe.get_all(
			"Stripe Webhook Event",
			filters={"request": held.name},
			fields=["kind", "handled", "error", "creation"],
			order_by="creation asc",
		),
	}
	if held.tenant:
		said["workspace"] = {
			"id": held.tenant,
			"status": frappe.db.get_value("Tenant", held.tenant, "status"),
			"last_job": frappe.db.get_value(
				"Provisioning Job",
				{"tenant": held.tenant},
				["name", "status", "step", "error"],
				as_dict=True,
				order_by="creation desc",
			),
		}
	return said


def price_list(
	offering: Annotated[str, "One offering's key, to also list the workspaces that have it."] | None = None,
) -> dict:
	"""For an operator of One only: the price list. Every offering, enabled
	or not, with its kind, price, whether it recurs, its trial, what it
	gives, and how many workspaces have it; with `offering`, also which
	workspaces. Changes nothing."""
	if not _operator():
		return {"error": "Only an operator of One, on the admin site, sees the price list."}
	from onedesk.one_admin import operator

	rows = frappe.get_all(
		"Offering",
		fields=["name", "label", "kind", "enabled", "amount", "currency", "recurring", "trial_days", "gives"],
		order_by="sort_key asc",
	)
	said = {"offerings": []}
	for one in rows:
		sold = operator.sold(one.name)
		said["offerings"].append(
			{
				"key": one.name,
				"label": one.label,
				"kind": one.kind,
				"enabled": bool(one.enabled),
				"price": f"{one.amount} {one.currency}" + (" a month" if one.recurring else " once"),
				"trial_days": one.trial_days or 0,
				"gives": one.gives,
				"workspaces": sold["all"],
				"live": sold["live"],
			}
		)
	if offering and frappe.db.exists("Offering", offering):
		names = operator.sold(offering)["workspaces"][:50]
		said["workspaces_with_it"] = frappe.get_all(
			"Tenant", filters={"name": ["in", names or [""]]}, fields=["name", "workspace_name", "status"]
		)
	return said


def plan_quote(
	seats: Annotated[int, "How many people need a seat."] = 0,
	storage_gb: Annotated[float, "How many GB of files."] = 0,
	database_gb: Annotated[float, "How many GB of database."] = 0,
	credits_a_month: Annotated[int, "How many OneCredits a month."] = 0,
	workspace: Annotated[str, "A workspace's id, to start from what it has now instead."] | None = None,
) -> dict:
	"""For an operator of One only: what a workspace needing this much should
	buy, as Plan Calculator answers it. Every plan with the add-ons that bring
	it up to the needs, cheapest first, with what each costs a month and what
	it costs us. With `workspace`, the needs are what it has now, and the plan
	it is on is marked. Changes nothing."""
	if not _operator():
		return {"error": "Only an operator of One, on the admin site, sees the plan calculator."}
	from onedesk.one_admin.report.plan_calculator import plan_calculator

	held = None
	if workspace:
		if not frappe.db.exists("Tenant", workspace):
			return {"error": f"There is no workspace {workspace}. Ask which one they meant."}
		held = frappe.db.get_value("Tenant", workspace, "offering")
		needs = plan_calculator.needs_of(workspace)
	else:
		needs = {
			"seats": seats,
			"storage_gb": storage_gb,
			"database_gb": database_gb,
			"credits_a_month": credits_a_month,
		}
	options, currency = plan_calculator.quote(needs)
	return {
		"needs": needs,
		"currency": currency,
		"options": [
			{
				"plan": one["plan"].label,
				"add_ons": [f"{count} × {extra.label}" for extra, count in one["extras"]],
				"a_month": one["monthly"],
				"costs_us": one["costs_us"],
				"cannot_reach": one["unmet"],
				"their_plan": bool(held) and one["plan"].key == held,
			}
			for one in options
		],
	}
