"""OneAI on the workspace's own settings (one/agent.py lists these tools):
its people and their access, reports, announcements, webhooks, the audit
log, privacy requests, intake, holidays, OneAI's switches, the plan and
signing in, each read as its administrators see it, and holidays changed
as a card."""

from typing import Annotated

import frappe
from frappe import _


def workspace_people() -> dict:
	"""Everybody on this workspace, for its administrators: which apps each
	may use and at what level, who administers it, when each was last active,
	who is turned off, and the seats."""
	from onedesk.one import roles
	from onedesk.account_center import center

	if not roles.administers():
		return {"error": "Only a workspace administrator sees everybody's access."}
	said = center._people()
	return {
		"seats": said["seats"] or "no limit",
		"used": said["used"],
		"people": [
			{
				"name": one["full_name"] or one["name"],
				"address": one["name"],
				"on": bool(one["enabled"]),
				"administrator": one["admin"],
				"apps": {app: level for app, level in one["access"].items() if level != "None"},
				"last_active": str(one["last_active"]) if one["last_active"] else "never",
			}
			for one in said["people"]
		],
		"next": "Everybody has One, OneCloud, OneMail, OneTask and OneCalendar anyway. Name people by name. "
		"The administrator changes a person on People in AccountCenter by clicking them.",
	}


def workspace_access() -> dict:
	"""Access, for this workspace's administrators: every level of each app,
	its user, manager and the ones made between, with what each may do and who
	is at it, the profiles
	with the levels they set and who is on them, the groups with their people,
	and who is held to which records."""
	from onedesk.one import access, roles

	if not roles.administers():
		return {"error": "Only a workspace administrator sees who may do what."}
	levels = []
	for app, names in access.all_levels().items():
		for tier in ["User", *names, "Manager"]:
			one = access.level(access.key_of(app, tier))
			levels.append(
				{
					"level": tier,
					"app": app,
					"made_by_the_workspace": bool(one["own"]),
					"may": {
						row["doctype"]: [access.SAID[r] for r in access.RIGHTS if row.get(r)]
						for row in one["rows"]
					},
					"people": one["people"],
				}
			)
	holds = frappe.get_all(
		"User Permission",
		filters={"allow": ["in", access.RECORD_KINDS]},
		fields=["user", "allow", "for_value", "applicable_for"],
		limit=200,
	)
	return {
		"levels": levels,
		"profiles": [
			{
				"profile": one["name"],
				"sets": {app: level for app, level in one["levels"].items() if level != "None"},
				"people": one["people"],
			}
			for one in access.profiles()
		],
		"groups": [
			{
				"group": one["name"],
				"people": frappe.get_all(
					"User Group Member",
					filters={"parent": one["name"], "parenttype": "User Group"},
					pluck="user",
				),
			}
			for one in access.groups()
		],
		"held_to": [
			{
				"person": one.user,
				"kind": one.allow,
				"record": one.for_value,
				"only_on": one.applicable_for or "everywhere",
			}
			for one in holds
		],
		"next": "Every level, User and Manager too, may be given or have taken away anything on the kinds its app works with. "
		"The administrator changes all of this on AccessCenter › Roles and Profiles, "
		"and a person's level, profile and what they are held to on their page under People.",
	}


def workspace_reports() -> dict:
	"""Reports and dashboards: the reports saved from a list (each one's kind
	of record, who saved it, and whether it is in everybody's sidebar), the
	dashboards with what each chart and card counts, and, for the workspace's
	administrators, the reports that go out by mail."""
	from onedesk.one import roles

	saved = frappe.get_list(
		"Report",
		filters={"report_type": "Report Builder", "is_standard": "No"},
		fields=["name", "ref_doctype", "owner"],
		limit=100,
	)
	placed = frappe.get_all(
		"Sidebar Item",
		filters={"parenttype": "Custom Sidebar", "link_type": "Report", "added": 1},
		fields=["link_to", "parent"],
	)
	shared = {row.link_to for row in placed if not frappe.db.get_value("Custom Sidebar", row.parent, "user")}
	dashboards = []
	for name in frappe.get_list("Dashboard", filters={"is_standard": 0}, pluck="name", limit=50):
		doc = frappe.get_doc("Dashboard", name)
		said = {"dashboard": name, "charts": [], "cards": []}
		for row in doc.charts:
			chart = (
				frappe.db.get_value(
					"Dashboard Chart",
					row.chart,
					[
						"chart_type",
						"document_type",
						"report_name",
						"based_on",
						"value_based_on",
						"group_by_based_on",
					],
					as_dict=True,
				)
				or {}
			)
			said["charts"].append({"chart": row.chart, **{k: v for k, v in chart.items() if v}})
		for row in doc.cards:
			card = (
				frappe.db.get_value(
					"Number Card",
					row.card,
					["type", "document_type", "function", "report_name"],
					as_dict=True,
				)
				or {}
			)
			said["cards"].append({"card": row.card, **{k: v for k, v in card.items() if v}})
		dashboards.append(said)
	mailed = []
	if roles.administers():
		mailed = [
			{
				"report": one.report,
				"how_often": one.frequency,
				"to": one.email_to,
				"on": bool(one.enabled),
				"runs_as": one.user,
			}
			for one in frappe.get_all(
				"Auto Email Report", fields=["report", "frequency", "email_to", "enabled", "user"], limit=100
			)
		]
	return {
		"saved_reports": [
			{
				"report": one.name,
				"of": one.ref_doctype,
				"saved_by": one.owner,
				"in_everybody's_sidebar": one.name in shared,
			}
			for one in saved
		],
		"dashboards": dashboards,
		"reports_by_mail": mailed,
		"next": "A list's Report view is saved from its menu (Save As) and lands under Saved Reports in its app. "
		"Dashboards are on each app's rail and made under OneStudio › Dashboards; reports by mail under Automation › Reports by Mail, set from a report's "
		"menu (Setup Auto Email). How is in One's documentation under Reports and dashboards (how_to).",
	}


def announcements(
	title: Annotated[str, "Only the announcement with this title, or part of it."] | None = None,
) -> dict:
	"""The workspace's announcements, newest first: what each says, who
	posted it, until when it shows on sign-in, and, for an administrator,
	who has seen it and who has not."""
	from onedesk.one import roles
	from onedesk.one.people import NOT_PEOPLE

	filters = {"public": 1}
	if title:
		filters["title"] = ["like", f"%{title}%"]
	rows = frappe.get_list(
		"Note",
		filters=filters,
		fields=["name", "title", "content", "owner", "creation", "notify_on_login", "expire_notification_on"],
		order_by="creation desc",
		limit=10,
	)
	everybody = frappe.get_all(
		"User",
		filters={"enabled": 1, "user_type": "System User", "name": ["not in", list(NOT_PEOPLE)]},
		pluck="name",
	)
	sees = roles.administers()
	said = []
	for one in rows:
		item = {
			"title": one.title,
			"says": frappe.utils.strip_html(one.content or "")[:600],
			"by": frappe.utils.get_fullname(one.owner),
			"posted": str(one.creation),
			"shown_on_sign_in_until": str(one.expire_notification_on) if one.notify_on_login else None,
		}
		if sees:
			seen = set(frappe.get_all("Note Seen By", filters={"parent": one.name}, pluck="user"))
			item["seen_by"] = len(seen & set(everybody))
			item["not_seen_by"] = [frappe.utils.get_fullname(u) for u in everybody if u not in seen][:50]
		said.append(item)
	return {
		"announcements": said,
		"how": "Announcements in the sidebar. An administrator posts one; everybody is told on the bell and by "
		"mail, and it pops up when they next sign in until the day it is shown until.",
	}


def webhooks(
	days: Annotated[int, "How many days of calls to look at, 7 if not said."] = 7,
) -> dict:
	"""The workspace's webhooks, for an administrator: each one's kind of
	record, event, where it sends (the host only), whether it is on, and how
	its calls went: delivered, failed and to be tried again, or given up,
	with what the other system answered the last few times it gave up."""
	from urllib.parse import urlparse

	from onedesk.one import roles
	from onedesk.one import webhooks as hooks

	if not roles.administers():
		return {"error": "Only a workspace administrator sees the webhooks."}
	since = frappe.utils.add_days(frappe.utils.now_datetime(), -max(1, min(int(days or 7), 90)))
	said = []
	for one in frappe.get_list(
		hooks.WEBHOOK,
		fields=["name", "webhook_doctype", "webhook_docevent", "request_url", "enabled", "max_retries"],
		limit=50,
	):
		calls = frappe.get_list(
			hooks.LOG,
			filters={"webhook": one.name, "creation": [">=", since]},
			fields=["status", {"COUNT": "*", "as": "calls"}],
			group_by="status",
		)
		gave_up = frappe.get_list(
			hooks.LOG,
			filters={"webhook": one.name, "status": "Exhausted", "creation": [">=", since]},
			fields=["reference_document", "response", "creation"],
			order_by="creation desc",
			limit=3,
		)
		said.append(
			{
				"webhook": one.name,
				"kind": one.webhook_doctype,
				"when": one.webhook_docevent,
				"sends_to": urlparse(one.request_url or "").hostname or "",
				"on": bool(one.enabled),
				"tries_again": one.max_retries or 0,
				"calls": {row.status or "Sending": row.calls for row in calls},
				"last_given_up": [
					{
						"record": row.reference_document,
						"answer": (row.response or "")[:300],
						"at": str(row.creation),
					}
					for row in gave_up
				],
			}
		)
	return {
		"days": days,
		"webhooks": said,
		"how": "Automation > Webhooks. A webhook sends every record of its kind on its event; to send only some, "
		"use an automation with a Call Webhook step. It goes over https to a public address.",
	}


def audit_log(
	what: Annotated[str, "changes, sign-ins or exports; changes if not said."] = "changes",
	kind: Annotated[str, "Only changes to, or exports of, this kind of record, such as Item."] | None = None,
	record: Annotated[str, "Only changes to this one record, by its name; give kind too."] | None = None,
	person: Annotated[str, "Only what this person did, by their address."] | None = None,
	days: Annotated[int, "How many days back to look, 7 if not said."] = 7,
) -> dict:
	"""The Audit Log, for a workspace administrator: who changed which record
	and each field from what to what, who signed in from where and whether it
	failed, or who exported or printed what. Only of the kinds of record the
	reader may read, never the system's own."""
	from onedesk.one import audit, roles

	if not roles.administers():
		return {
			"error": "Only a workspace administrator reads the Audit Log; a record's own timeline shows "
			"its changes."
		}
	since = frappe.utils.add_days(frappe.utils.now_datetime(), -max(1, min(int(days or 7), 365)))
	filters = {"creation": [">=", since]}
	if what == "sign-ins":
		if person:
			filters["user"] = person
		rows = frappe.get_list(
			"Activity Log",
			filters=filters,
			fields=["user", "operation", "status", "ip_address", "creation"],
			order_by="creation desc",
			limit=100,
		)
		said = [
			{
				"who": one.user,
				"did": one.operation,
				"failed": one.status != "Success",
				"from": one.ip_address,
				"when": str(one.creation),
			}
			for one in rows
		]
		return {"sign_ins": said, "open": "/desk/activity-log"}
	if what == "exports":
		if person:
			filters["user"] = person
		if kind:
			filters["export_from"] = kind
		rows = frappe.get_list(
			"Access Log",
			filters=filters,
			fields=["user", "export_from", "reference_document", "report_name", "file_type", "creation"],
			order_by="creation desc",
			limit=100,
		)
		said = [
			{
				"who": one.user,
				"kind": one.export_from,
				"record": one.reference_document,
				"report": one.report_name,
				"as": one.file_type,
				"when": str(one.creation),
			}
			for one in rows
		]
		return {"exports": said, "open": "/desk/access-log"}
	if person:
		filters["owner"] = person
	if kind:
		filters["ref_doctype"] = kind
	if record:
		filters["docname"] = record
	rows = frappe.get_list(
		"Version",
		filters=filters,
		fields=["name", "owner", "ref_doctype", "docname", "data", "creation"],
		order_by="creation desc",
		limit=60,
	)
	changes = []
	for one in rows:
		data = audit.seen(one.data, one.ref_doctype)
		meta = frappe.get_meta(one.ref_doctype)
		changes.append(
			{
				"who": one.owner,
				"kind": one.ref_doctype,
				"record": one.docname,
				"when": str(one.creation),
				"fields": [
					{"field": meta.get_label(f) or f, "from": o, "to": n}
					for f, o, n in (data.get("changed") or [])[:12]
				],
				"rows_added": len(data.get("added") or []),
				"rows_removed": len(data.get("removed") or []),
				"rows_changed": len(data.get("row_changed") or []),
				"open": f"/desk/version/{one.name}",
			}
		)
	return {
		"changes": changes,
		"next": "A change opens with every field it changed; Open on its row goes to the record.",
	}


def privacy_request(
	name: Annotated[
		str, "The request, by its name: a copy's id, or a deletion such as deleted-user-0001@example.com."
	],
) -> dict:
	"""For a workspace administrator: what a privacy request would give or do,
	without doing it. For a copy, each kind of data and how much of it. For a
	deletion, what approving it would do. What is deleted outright,
	where their name and address are taken out, what is still assigned to
	them, whether they have an employee record (HR's, which stays), and
	anything that stops it (the last administrator, the person billed)."""
	from onedesk.one import privacy, roles

	if not roles.administers():
		return {"error": "Only a workspace administrator decides privacy requests."}
	if frappe.db.exists(privacy.DOWNLOAD, name):
		from onedesk.one import privacy_copy

		return {
			**privacy_copy.review(name),
			"next": "Review and Send on the request: what is about the person always goes; mail, comments, "
			"to-dos, conversations, changes, exports and notifications may be withheld only to protect other "
			"people or the company's confidential information, with a reason the person is told.",
		}
	if not frappe.db.exists(privacy.DELETION, name):
		return {"error": f"There is no request {name}."}
	return {
		**privacy.preview(name),
		"next": "Approve and Delete, or Hold with a reason, on the request; how is in One's documentation "
		"under Privacy Requests (how_to).",
	}


def workspace_intake() -> dict:
	"""OneAI's reading settings and this month, for the workspace's administrators:
	each setting with what it means now, and what arrived, what OneAI handled,
	what needed a person, what waits and what was undone."""
	from onedesk.one import roles
	from onedesk.one_ai import yours

	if not roles.administers():
		return {"error": "Only a workspace administrator sees OneAI's reading settings."}
	said = yours._intake()
	labels = {one["fieldname"]: one["label"] for one in said["fields"]}
	return {
		"settings": {labels.get(name, name): value for name, value in said["values"].items()},
		"meaning": {
			"confidence_floor": "what OneAI is less sure of than this percentage waits for a person",
			"quiet_minutes": "0 means OneAI acts on a matter at once",
			"household": "on means no draft bills or invoices at all",
			"submit_matching_e_invoices": "on means OneAI submits e-invoices from known suppliers that match an order",
		},
		"this_month": said["month"],
		"mailboxes_read": [
			{"mailbox": one["email"], "on_behalf_of": one["for"]} for one in said["mailboxes"] if one["on"]
		],
		"mailboxes_not_read": [one["email"] for one in said["mailboxes"] if not one["on"]],
		"folders_read": [{"folder": one["path"], "on_behalf_of": one["for"]} for one in said["folders"]],
	}


def workspace_holidays() -> dict:
	"""The holiday list in force, for the workspace's administrators: its days,
	when it ends, the list after it if any, the public holidays the country
	has that it lacks, and how many people are on a list of their own."""
	from onedesk.one import roles
	from onedesk.one_hr import control as hr_control
	from onedesk.one_hr import holidays

	if not roles.administers():
		return {"error": "Only a workspace administrator sees the workspace's holidays."}
	said = hr_control._holidays()
	if said.get("empty"):
		return {
			"holiday_list": None,
			"meaning": "no list: every day is a working day for leave and attendance",
		}
	listed = said["list"]
	values = said["values"]
	missing = []
	if values.get("country"):
		held = {one["holiday_date"] for one in values["holidays"]}
		try:
			found = holidays.country_holidays(
				values["country"], listed["from_date"], listed["to_date"], values.get("subdivision")
			)
		except Exception:
			found = []
		missing = [one for one in found if one["holiday_date"] not in held]
	return {
		"holiday_list": listed["name"],
		"from": listed["from_date"],
		"to": listed["to_date"],
		"days_left": listed["days_left"],
		"days_off_each_week": listed["weekly"],
		"country": values.get("country"),
		"public_holidays": values["holidays"],
		"next_list": said["next"],
		"meaning": "with no next list, from the day after the last day every day counts as a working day for leave and attendance",
		"country_holidays_not_in_the_list": missing,
		"people_on_their_own_list": said["elsewhere"],
	}


def my_day() -> dict:
	"""What waits for the reader today, as One's Home counts it: tasks due or
	late (with the first few), meetings today, documents waiting in Documents,
	OneAI suggestions waiting for their approval, approvals waiting on them,
	and for an administrator what in the workspace needs them."""
	from onedesk.one import home

	return home.my_day()


def change_holidays(
	add: Annotated[
		list[dict],
		"Days to add or rename, each {date, name}: date as YYYY-MM-DD. A closure of several days is one entry per day.",
	]
	| None = None,
	remove: Annotated[list[str], "Dates to take off the list, as YYYY-MM-DD."] | None = None,
	days_off: Annotated[
		list[str],
		"The week's days off from now on, in English (Monday to Sunday): every one of them, not only a new one.",
	]
	| None = None,
	why: Annotated[str, "In a sentence, what the change is for."] | None = None,
) -> dict:
	"""Suggest a change to the workspace's holidays, as a card a workspace
	administrator approves: a public holiday or a day the workplace is closed
	added, renamed or removed, and the week's days off (a weekend of two is
	two days). Read workspace_holidays first. The dates go on the list whose
	year holds them. Nothing changes until they approve it. Workspace
	administrators only."""
	from frappe.utils import formatdate, getdate

	from onedesk.one import roles
	from onedesk.one_ai import proposals
	from onedesk.one_hr import control as hr_control
	from onedesk.one_hr import holidays

	if not roles.administers():
		return {"error": "Only a workspace administrator changes the workspace's holidays."}
	given = [one.get("date") for one in (add or []) if isinstance(one, dict)] + list(remove or [])
	try:
		days = [getdate(day) for day in given]
	except Exception:
		return {"error": "Give every date as YYYY-MM-DD."}
	covering = set()
	for day in days:
		found = holidays.covering(day)
		if not found:
			return {
				"error": f"No holiday list holds {day}. Next year's list is made with Create Next Year's List on "
				"OneHR's ControlCenter › Holidays; suggest this once it is there."
			}
		covering.add(found)
	if len(covering) > 1:
		return {
			"error": f"Those dates are on {len(covering)} lists ({', '.join(sorted(covering))}); suggest each list's days apart."
		}
	target = covering.pop() if covering else holidays.in_force()
	if not target:
		return {"error": "The workspace has no holiday list yet."}
	said = hr_control._holidays(target)
	values = said["values"]
	rows = {one["holiday_date"]: one["description"] for one in values["holidays"]}
	was_off = list(said["list"]["weekly"])
	summary = []
	for one in add or []:
		day, name = str(getdate(one.get("date"))), (one.get("name") or "").strip()
		if not name:
			return {"error": f"Give {day} a name, such as the holiday or why the workplace is closed."}
		label = _("Rename") if day in rows else _("Add")
		if rows.get(day) == name:
			continue
		value = f"{formatdate(day)} · {name}"
		summary.append(
			{"label": label, "value": _("{0} (was {1})").format(value, rows[day]) if day in rows else value}
		)
		rows[day] = name
	for one in remove or []:
		day = str(getdate(one))
		if day not in rows:
			return {
				"error": f"{day} is not a holiday on {target}. A weekly day off is changed with days_off."
			}
		summary.append({"label": _("Remove"), "value": f"{formatdate(day)} · {rows.pop(day)}"})
	off = was_off
	if days_off is not None:
		named = {day.lower(): day for day in holidays.WEEK}
		wrong = [one for one in days_off if str(one).strip().lower() not in named]
		if wrong:
			return {"error": f"{', '.join(map(str, wrong))}: say a weekday in English, Monday to Sunday."}
		off = [day for day in holidays.WEEK if day.lower() in {str(one).strip().lower() for one in days_off}]
		if off != was_off:
			summary.append(
				{
					"label": _("Days Off Each Week"),
					"value": _("{0} (was {1})").format(
						", ".join(_(day) for day in off) or _("none"),
						", ".join(_(day) for day in was_off) or _("none"),
					),
				}
			)
	if not summary:
		return {
			"error": "That is what the list already says, so there is nothing to change. Say it is right as it is."
		}
	return {
		"proposal": proposals.propose(
			"Holidays",
			"Holiday List",
			changes={
				"modified": said["opened"][0]["modified"],
				"values": {
					"weekly_offs": off,
					"country": values.get("country"),
					"subdivision": values.get("subdivision"),
					"holidays": [
						{"holiday_date": day, "description": name} for day, name in sorted(rows.items())
					],
				},
				"summary": summary,
			},
			record=target,
			why=why,
		),
		"state": "Proposed",
		"next": "Tell them leave, attendance, check-ins, the calendar and deadlines count around it once they "
		"approve it, and that OneHR's ControlCenter › Holidays shows the whole list.",
	}


def workspace_oneai() -> dict:
	"""OneAI here, for the workspace's administrators: what each of its jobs
	used in the last thirty days, and which records get a summary. One picks
	the models, by tier; nothing about them is set here."""
	from frappe.utils import add_days, getdate

	from onedesk.one import roles
	from onedesk.one_ai import brief
	from onedesk.one_ai.report.ai_credits import ai_credits

	if not roles.administers():
		return {"error": "Only a workspace administrator sees OneAI's jobs."}
	end = getdate()
	try:
		_columns, rows, *_rest = ai_credits.execute({"from_date": add_days(end, -29), "to_date": end, "by": "Job"})
	except frappe.ValidationError:
		rows = []
	return {
		"last_30_days": [{"job": one["what"], "calls": one["calls"], "credits": one["credits"]} for one in rows],
		"summaries": [{"record": one["label"], "on": one["on"], "written": one["written"]} for one in brief.settings()],
	}


DOMAIN_STATES = {
	"Active": "working",
	"Pending": "added; waiting for its CNAME, or a TXT record at _one.<domain>, to name the workspace's own address "
	"(cname_target), and for Cloudflare to issue its certificate, which it does by itself within minutes of the "
	"record being right",
	"Broken": "Cloudflare gave up issuing its certificate, almost always because the CNAME was never made or "
	"points elsewhere; fix the record, then remove the domain and add it again",
	"Gone": "Cloudflare no longer has it; remove it and add it again",
}


def _domains() -> dict:
	"""The workspace's addresses as `workspace_plan` hands them over: each
	domain, whether it works and what that means, which is the main address,
	and the CNAME target. Asks the account again when what it said is stale
	(account_center/center.py, _domains)."""
	from onedesk.account_center import center

	said = center._domains()
	return {
		"cname_target": said["target"],
		"domains": [
			{
				"domain": one["domain"],
				"given_by_one": bool(one["given"]),
				"main_address": bool(one["primary"]),
				"status": one["status"],
				"means": DOMAIN_STATES.get(one["status"], "not working"),
				"cloudflare_says": one.get("problem"),
			}
			for one in said["domains"]
		],
	}


def workspace_plan() -> dict:
	"""The workspace's plan, OneCredits and domains, for its administrators:
	plan, seats, storage, credits left, held, used in the last thirty days and
	what expires when, the last thirty days by model and by person, the ledger
	(what came in and what OneAI used each day), and each of its addresses:
	whether it works and what that means, which is the main one, and the CNAME
	target a domain of its own has to point at."""
	from frappe.utils import add_days, getdate

	from onedesk.one import roles
	from onedesk.account_center import center
	from onedesk.one_ai.report.ai_credits import ai_credits

	if not roles.administers():
		return {"error": "Only a workspace administrator sees the plan and the credits."}
	said = center._plan()
	held = said["account"]
	end = getdate()
	cut = {}
	for by in ("Job", "Person"):
		try:
			_columns, rows, *_rest = ai_credits.execute(
				{"from_date": add_days(end, -29), "to_date": end, "by": by}
			)
		except frappe.ValidationError:
			rows = []
		cut[by.lower()] = rows[:10]
	return {
		"standing": (said["state"] or {}).get("label"),
		"news": (said["said"] or {}).get("text"),
		"plan": held["plan"],
		"a_month": held["monthly"],
		"seats": {"used": said["used"], "of": held["seats"] or "no limit"},
		"storage": said["storage"],
		"database": said["database"],
		"added_to_the_plan": said["add_ons"],
		"cheapest_for_what_is_used": _cheapest(said),
		"credits": {
			"left": held["credits_balance"],
			"held": held["credits_held"],
			"used_in_30_days": held["credits_month"],
			"expiring": held["credits_expiring"],
			"expire_on": str(held["credits_expires_on"]) if held["credits_expires_on"] else None,
		},
		"last_30_days": cut,
		"ledger": (said["ledger"] or [])[:40],
		"closing": said["closing"],
		**_domains(),
		"as_of": str(held["last_heard"]) if held["last_heard"] else None,
		"next": "The plan's monthly credits expire at the end of the month and are used first; bought credits last 12 months. Credits "
		"are bought from Buy Credits in the page head of Plan and Credits in AccountCenter.",
	}


def _cheapest(said: dict) -> list | None:
	"""The three cheapest ways to have what the workspace uses now, from the
	account's calculator (one_admin/plans.py). No AI call; None when the
	account cannot be reached."""
	from onedesk.one import account

	held = said["account"]
	gb = 1000 * 1000 * 1000
	needs = {
		"seats": said["used"],
		"storage_gb": -(-frappe.utils.cint(held["storage_bytes"]) // gb),
		"database_gb": -(-frappe.utils.cint(held["database_bytes"]) // gb),
	}
	try:
		quoted = account.plans_quote(needs)
	except Exception:
		return None
	return [
		{
			"plan": one["label"],
			"add_ons": [f"{extra['count']} × {extra['label']}" for extra in one["extras"]],
			"a_month": one["monthly"],
			"against_now": one["change"],
		}
		for one in quoted.get("options", [])[:3]
	]


def workspace_sign_in() -> dict:
	"""How people sign in to this workspace, for its administrators: the rules
	(two-factor and for whom, passkey and email link sign-in, one device at a
	time, how long a session lasts unused, the password rule, the lockout,
	password expiry, whether records may be shared) and how people follow them: how many people
	there are, how many administer it, whose password is over a year old, and
	the failed sign-ins of the last week."""
	from frappe.utils import add_days, add_to_date, now_datetime

	from onedesk.one import control, roles

	if not roles.administers():
		return {"error": "Only a workspace administrator sees how everybody signs in."}
	system = frappe.get_single("System Settings")
	people = frappe.get_all(
		"User",
		filters={"enabled": 1, "user_type": "System User", "name": ["not in", ("Administrator", "Guest")]},
		pluck="name",
	)
	year_ago = add_to_date(now_datetime(), years=-1)
	stale = [
		one.name
		for one in frappe.get_all(
			"User",
			filters={"name": ["in", people or [""]]},
			fields=["name", "last_password_reset_date", "creation"],
		)
		if (one.last_password_reset_date and str(one.last_password_reset_date) < str(year_ago.date()))
		or (not one.last_password_reset_date and one.creation < year_ago)
	]
	failed = frappe.get_all(
		"Activity Log",
		filters={
			"operation": "Login",
			"status": ["!=", "Success"],
			"creation": [">", add_days(now_datetime(), -7)],
		},
		fields=["user", "ip_address", "creation"],
		order_by="creation desc",
		limit=20,
	)
	return {
		"two_factor": control._two_factor(system),
		"two_factor_by": system.two_factor_method if system.enable_two_factor_auth else None,
		"passkey_sign_in": bool(system.get("one_login_with_passkey")),
		"email_link_sign_in": bool(system.login_with_email_link),
		"one_device_at_a_time": bool(system.deny_multiple_sessions),
		"lockout": f"after {system.allow_consecutive_login_attempts or 'unlimited'} wrong passwords, for {system.allow_login_after_fail or 60} seconds",
		"passwords_expire_after_days": system.force_user_to_reset_password or None,
		"record_sharing": not system.disable_document_sharing,
		"signed_out_after_unused": system.session_expiry or "240:00",
		"password_rule": f"score {system.minimum_password_score} of 4"
		if system.enable_password_policy
		else "any password",
		"people": len(people),
		"administrators": len([one for one in people if roles.administers(one)]),
		"passwords_over_a_year_old": len(stale),
		"failed_sign_ins_last_week": [
			{"user": one.user, "address": one.ip_address, "on": str(one.creation)} for one in failed
		],
		"next": "Say plainly what is fine and what to change, most important first. Two-factor for everybody, "
		"or at least administrators, is the usual advice; failed sign-ins from one address are worth naming. "
		"They change the rules themselves under One's ControlCenter › Sign-in.",
	}


def my_sign_in() -> dict:
	"""How the person asking signs in and where they are signed in: when their
	password last changed, whether they have a passkey and what it is for,
	whether two-factor sign-in applies to them, the devices they are signed in
	on, and their last sign-ins, failed ones included."""
	from onedesk.account_center import signin

	said = signin.facts()
	return {
		"password_last_changed": str(said["password_changed"])
		if said["password_changed"]
		else "never recorded",
		"passkey": bool(said["passkey"]),
		"passkey_signs_in": said["passkey_signs_in"],
		"passkey_checks_in": said["passkey_clocks"],
		"two_factor": said["two_factor"],
		"signed_in_on": [
			{
				"device": one["device"],
				"address": one["address"],
				"last_used": str(one["last_used"]),
				"this_one": one["here"],
			}
			for one in said["sessions"]
		],
		"recent_sign_ins": [
			{"failed": one["failed"], "address": one["address"], "on": str(one["on"])}
			for one in said["recent"]
		],
		"next": "Say plainly what looks fine and what to do: an old password, no two-factor, places they do not "
		"recognise, failed sign-ins they did not make. They change it themselves on Sign-in in AccountCenter.",
	}
