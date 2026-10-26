"""AICenter (docs/AICENTER.md): OneAI for a workspace. On or off, its tier,
what each module does on its own, which records get a summary, Knowledge,
and what was used; and for everybody, what OneAI keeps about them. Every
value stays where it was kept; this only reads and writes it."""

import importlib

import json

import frappe
from frappe import _, _lt

from onedesk.one import account, apps, roles
from onedesk.one_ai import models

TIER = "one_ai_tier"

# What each tier means to the person choosing it.
TIERS = {
	"fast": (_lt("Fast"), _lt("Quick answers for everyday questions, at the lowest cost.")),
	"balanced": (_lt("Balanced"), _lt("Careful answers at a modest cost. Right for most workspaces.")),
	"full": (_lt("Full"), _lt("The strongest models, for the hardest questions. The dearest.")),
}

# Modules whose `ai.py` declares `JOBS`: what OneAI does there on its own, as
# a single's fields, each drawn with its own label and description.
PARTS = {"OneHR": "onedesk.one_hr.ai"}


def may() -> dict:
	"""What the reader may open of AICenter beyond Yours: everything, for a
	workspace administrator; Usage, for a role that holds it (abilities.py)."""
	from onedesk.one import abilities

	admin = roles.administers()
	return {"all": admin, "usage": admin or abilities.may("AI Knowledge", "ai_usage")}


def modules() -> list[str]:
	"""The modules AICenter has a part for, for their ControlCenter."""
	return [*PARTS, "OneMail"]


def tier() -> str:
	"""The workspace's tier, Balanced until an administrator chooses."""
	held = frappe.db.get_default(TIER)
	return held if held in models.TIERS else models.USUAL


@frappe.whitelist()
def state() -> dict:
	"""The OneAI part: on or off, the tier, what an answer costs at each, and
	the credits left."""
	roles.require()
	return {"on": apps.ai_on(), "tier": tier(), "tiers": _tiers(), "credits": _credits()}


def _tiers() -> list[dict]:
	costs = {}
	if account.configured():
		try:
			costs = {one["tier"]: one["credits"] for one in account.ask("onedesk.one_admin.proxy.ai_tiers") or []}
		except Exception:
			frappe.log_error(title="AICenter could not ask the account what each tier costs")
	return [
		{"tier": key, "label": str(label), "about": str(about), "credits": costs.get(key)}
		for key, (label, about) in TIERS.items()
	]


def _credits() -> float | None:
	held = frappe.db.get_single_value("Workspace Account", "credits_balance")
	return float(held) if held is not None else None


@frappe.whitelist(methods=["POST"])
def set_tier(tier: str) -> str:
	roles.require()
	if tier not in models.TIERS:
		frappe.throw(_("Choose Fast, Balanced or Full."))
	frappe.db.set_default(TIER, tier)
	return tier


@frappe.whitelist(methods=["POST"])
def set_on(on: int | str) -> bool:
	"""OneAI on or off for the whole workspace, as Apps turns it. What was
	off only because OneAI was (OneAI) comes back with it."""
	roles.require()
	held = json.loads(frappe.db.get_default(apps.KEY) or "[]")
	off = [one for one in held if one != apps.AI and apps.NEEDS.get(one) != apps.AI]
	if not frappe.utils.cint(on):
		off.append(apps.AI)
	apps.save(off)
	return apps.ai_on()


@frappe.whitelist()
def reading() -> dict:
	"""Reading what arrives: on or off, this month, what it may do, and the
	mailboxes and folders it reads."""
	from onedesk.one import settings

	roles.require()
	said = settings._intake()
	kinds = {"Switch": "switch", "Int": "number", "Percent": "number"}
	return {
		"on": apps.intake_on(),
		"month": said["month"],
		"settings": [
			{
				"key": one["fieldname"],
				"label": one["label"],
				"about": one["description"],
				"kind": kinds[one["fieldtype"]],
				"value": said["values"].get(one["fieldname"]),
			}
			for one in said["fields"]
			if one["fieldtype"] in kinds
		],
		"mailboxes": said["mailboxes"],
		"folders": said["folders"],
	}


@frappe.whitelist(methods=["POST"])
def set_reading(key: str, value) -> None:
	"""One of reading's settings, saved as Settings saved it, which tells the
	other administrators of a change that matters (tell.intake_changed)."""
	from onedesk.one import settings

	roles.require()
	if key not in settings.INTAKE:
		frappe.throw(_("There is nothing called {0} here.").format(key))
	settings._save_intake({key: frappe.utils.flt(value)})


@frappe.whitelist(methods=["POST"])
def set_reading_on(on: int | str) -> bool:
	"""Reading on or off for the whole workspace, as Apps turns it."""
	roles.require()
	held = json.loads(frappe.db.get_default(apps.KEY) or "[]")
	off = [one for one in held if one != apps.INTAKE]
	if not frappe.utils.cint(on):
		off.append(apps.INTAKE)
	apps.save(off)
	return apps.intake_on()


@frappe.whitelist()
def parts() -> list[dict]:
	"""Each module's part: what OneAI does there on its own."""
	roles.require()
	out = []
	for module, path in PARTS.items():
		declared = getattr(importlib.import_module(path), "JOBS", [])
		out.append({"module": module, "jobs": [_job(one) for one in declared]})
	out.append({"module": "OneMail", "mailboxes": _mailboxes()})
	return out


def _job(declared: dict) -> dict:
	meta = frappe.get_meta(declared["single"])
	field = meta.get_field(declared["key"])
	return {
		"key": declared["key"],
		"label": _(field.label),
		"about": _(field.description) if field.description else None,
		"kind": "switch" if field.fieldtype == "Check" else "number",
		"value": frappe.db.get_single_value(declared["single"], declared["key"]),
	}


def _declared(key: str) -> dict:
	for path in PARTS.values():
		for one in getattr(importlib.import_module(path), "JOBS", []):
			if one["key"] == key:
				return one
	frappe.throw(_("There is nothing called {0} here.").format(key))


@frappe.whitelist(methods=["POST"])
def set_job(key: str, value) -> dict:
	"""One of a module's switches, or a number of days, saved on its single."""
	roles.require()
	declared = _declared(key)
	doc = frappe.get_single(declared["single"])
	doc.set(key, frappe.utils.cint(value))
	doc.flags.ignore_permissions = True
	doc.save()
	return _job(declared)


def _mailboxes() -> list[dict]:
	"""Each mailbox OneAI may read, and how far it reads new mail; the
	mailbox's own OneAI tab is where that is changed."""
	rows = frappe.get_all(
		"Email Account",
		or_filters={"one_hosted": 1, "one_connected": 1},
		fields=["name", "email_id", "one_ai_off", "one_intake", "one_ai_level"],
		order_by="email_id asc",
	)
	return [
		{
			"name": one.name,
			"email": one.email_id,
			"reads": bool(one.one_intake) and not one.one_ai_off,
			"level": _(one.one_ai_level) if one.one_ai_level else None,
		}
		for one in rows
	]


@frappe.whitelist()
def summaries() -> list[dict]:
	from onedesk.one_ai import brief

	roles.require()
	return brief.settings()


@frappe.whitelist()
def usage() -> dict:
	"""What each job used in the last thirty days, from the account."""
	from frappe.utils import add_days, getdate

	from onedesk.one_ai.report.ai_credits import ai_credits

	if not may()["usage"]:
		frappe.throw(_("Only a workspace administrator, or a role given Usage, sees what OneAI used."), frappe.PermissionError)
	if not account.configured():
		return {"reached": False, "jobs": []}
	end = getdate()
	try:
		_columns, rows, *_rest = ai_credits.execute({"from_date": add_days(end, -29), "to_date": end, "by": "Job"})
	except frappe.ValidationError:
		return {"reached": False, "jobs": []}
	return {"reached": True, "jobs": rows}


@frappe.whitelist()
def knowledge() -> list[dict]:
	roles.require()
	return frappe.get_all(
		"AI Knowledge", fields=["name", "title", "applies_to", "enabled"], order_by="title asc", limit=200
	)


@frappe.whitelist()
def yours() -> dict:
	"""What OneAI keeps about the reader, and the workspace's Knowledge it
	reads too."""
	from onedesk.one import settings

	return settings._memory()

