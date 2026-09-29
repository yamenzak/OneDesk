"""What OneAI does in OneAdmin: says what needs the operator, and why, and
how one workspace is doing.

The operator's own readers, on the admin site only and for One Operator only,
as every console read is (`operator._may`). `console_today` is Home's own list
(`home.needs`), so the panel and the page say the same thing;
`workspace_facts` is what a workspace's own form shows, its head and its
connections, and `job_facts` a job's walk in words. Nothing is changed from here: resuming a job, building a signup,
checking a domain or giving credits is a button the operator presses.
"""

from typing import Annotated

import frappe
from frappe import _lt

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
}


def page(said: dict) -> str | None:
	"""The sentence the model is told on OneAdmin's Home."""
	if said.get("workspace") != "One Admin":
		return None
	return (
		"The reader is an operator of One, on OneAdmin's Home: how many workspaces are live, being built, "
		"owing, failed, or paid for and not built, and a list of what needs them. console_today reads that "
		"list with each item's reason. Nothing is changed from the panel: Resume, Build It and Check Again "
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


def workspace_facts(
	workspace: Annotated[str, "The workspace's id, its slug, as the page names it."],
) -> dict:
	"""For an operator of One only: how one workspace stands. Its status and
	since when, whether it owes and when it falls a rung, its plan and
	add-ons, its storage against its limit, its OneAI credits and this month's
	spend, its domains, and its last jobs and log entries."""
	if not _operator():
		return {"error": "Only an operator of One, on the admin site, sees a workspace."}
	if not frappe.db.exists("Tenant", workspace):
		return {"error": f"There is no workspace {workspace}. Ask which one they meant."}
	from onedesk.one.heads import size
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
		"domains": frappe.get_all(
			"Tenant Domain", filters={"tenant": held.name}, fields=["domain", "status", "problem"]
		),
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
