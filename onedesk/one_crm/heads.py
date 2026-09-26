"""What a lead's and a deal's page say above their fields. See one/head.py.

A deal answers what it is worth and how likely, how long it has been in its
stage against how long deals usually stay there, what comes next and when,
when they were last in touch, when it should close, its quotation and where
it came from. A lead answers when it came in, whether and how fast it was
answered, what comes next, when they were last in touch and the deals made
from it. The figures are record.py's `overview`, worked out once per request.

A time since ("yesterday") is sent as the moment itself (`when`), and the
desk says it with frappe's own `prettyDate` when it draws the band, so it
reads as every other time on the desk does.
"""

import frappe
from frappe import _, _lt
from frappe.utils import fmt_money, formatdate, get_datetime, getdate, now_datetime, today
from frappe.utils.caching import request_cache

from onedesk.one_crm import capture, record
from onedesk.one_crm.next import OWNER

#: Where a record's time since goes in its label or value.
WHEN = "{when}"


@request_cache
def _said(doctype: str, name: str) -> dict:
	return record.overview(doctype, name)


def lasted(start, end=None) -> str:
	"""How long, not when: "under an hour", "5 hours", "12 days". Pure over
	the two moments."""
	hours = int((get_datetime(end or now_datetime()) - get_datetime(start)).total_seconds() // 3600)
	if hours < 1:
		return _("under an hour")
	if hours < 24:
		return _("an hour") if hours == 1 else _("{0} hours").format(hours)
	days = hours // 24
	return _("a day") if days == 1 else _("{0} days").format(days)


def days(count) -> str:
	"""A number of days as a person says it: "a day", "5 days", "under a day"."""
	whole = round(count or 0)
	if whole < 1:
		return _("under a day")
	return _("a day") if whole == 1 else _("{0} days").format(whole)


def _money(value, currency) -> str:
	return fmt_money(value or 0, precision=0, currency=currency)


# ------------------------------------------------------------------ a deal


def value(doc):
	said = _said(doc.doctype, doc.name)
	return {
		"label": _("Deal Value · {0}%").format(round(said["probability"])),
		"value": _money(said["value"], said["currency"]),
		"meter": {"value": said["probability"], "of": 100},
	}


def stage(doc):
	said = _said(doc.doctype, doc.name)
	stayed = lasted(said["since"])
	usual = said.get("usual")
	return {
		"label": _(named) if (named := said["stage"]) else _("Sales Stage"),
		"value": _("for {0} · usually {1}").format(stayed, days(usual))
		if usual is not None
		else _("for {0}").format(stayed),
		"tone": "waiting" if said.get("long") else None,
		# How far through the stage's usual time it is.
		"meter": {
			"value": int((now_datetime() - get_datetime(said["since"])).total_seconds() // 86400),
			"of": usual,
		}
		if usual
		else None,
	}


def closes(doc):
	said = _said(doc.doctype, doc.name)
	if not said.get("closing"):
		return None
	late = said["open"] and getdate(said["closing"]) < getdate(today())
	return {"value": formatdate(said["closing"]), "tone": "alarm" if late else None}


def quotation(doc):
	found = _said(doc.doctype, doc.name).get("quotation")
	if not found:
		return None
	return {
		"value": _("{0} · {1}").format(_(found.status), _money(found.grand_total, found.currency)),
		"route": f"/desk/quotation/{found.name}",
	}


# ------------------------------------------------------------------ a lead


def came_in(doc):
	return {"value": WHEN, "when": str(_said(doc.doctype, doc.name)["since"])}


def reply(doc):
	said = _said(doc.doctype, doc.name)
	if said.get("first_reply"):
		return {
			"label": _("First Reply"),
			"value": _("after {0}").format(lasted(said["since"], said["first_reply"])),
		}
	if said["open"]:
		return {"label": _("Waiting For a Reply"), "value": lasted(said["since"]), "tone": "waiting"}
	return None


def made_deals(doc):
	found = _said(doc.doctype, doc.name)["deals"]
	if not found["count"]:
		return None
	return {
		"value": _("{0} open of {1}").format(found["open"], found["count"]),
		"route": f"/desk/opportunity?opportunity_from=Lead&party_name={doc.name}",
	}


# ------------------------------------------------------------------ both


def next_step(doc):
	said = _said(doc.doctype, doc.name)
	if not said["open"]:
		return None
	step, on = said["next"]["step"], said["next"]["on"]
	if not step and not on:
		return {"value": _("None planned"), "tone": "waiting"}
	return {
		"label": _("Next Step") + (f" · {WHEN}" if on else ""),
		"value": step or _("Next Step"),
		"when": str(on) if on else None,
		"tone": "alarm" if on and get_datetime(on) < now_datetime() else None,
	}


def contact(doc):
	said = _said(doc.doctype, doc.name)
	last = said.get("contact")
	if not last:
		return {
			"label": _("Last Contact"),
			"value": _("None yet"),
			"tone": "waiting" if said["open"] else "quiet",
		}
	return {
		"label": _("Last Call") if last["kind"] == "Call" else _("Last Email"),
		"value": WHEN,
		"when": str(last["at"]),
		"route": f"/desk/{frappe.scrub(last['doctype']).replace('_', '-')}/{last['name']}",
	}


def source(doc):
	return _said(doc.doctype, doc.name).get("source") or None


MEASURES = {
	"crm.value": value,
	"crm.stage": stage,
	"crm.closes": closes,
	"crm.quotation": quotation,
	"crm.came_in": came_in,
	"crm.reply": reply,
	"crm.deals": made_deals,
	"crm.next_step": next_step,
	"crm.contact": contact,
	"crm.source": source,
}


VERBS = {
	# Nobody's yet: it came in from the web form or the inbox. See capture.py.
	"crm.take": {
		"doctypes": list(OWNER),
		"label": lambda doc: _("Take This Lead") if doc.doctype == "Lead" else _("Take This Deal"),
		"when": lambda doc: not doc.get(OWNER[doc.doctype]) and bool(doc.has_permission("write")),
		"fields": [],
		"run": lambda doc: capture.take(doc.doctype, doc.name) or _("It is yours."),
	},
}


HEADS = [
	{
		"doctype": "Opportunity",
		"band": [
			{"label": _lt("Deal Value"), "source": "Measure", "measure": "crm.value"},
			{"label": _lt("Sales Stage"), "source": "Measure", "measure": "crm.stage"},
			{"label": _lt("Next Step"), "source": "Measure", "measure": "crm.next_step"},
			{"label": _lt("Last Contact"), "source": "Measure", "measure": "crm.contact"},
			{"label": _lt("Closes"), "source": "Measure", "measure": "crm.closes"},
			{"label": _lt("Quotation"), "source": "Measure", "measure": "crm.quotation"},
			{"label": _lt("Source"), "source": "Measure", "measure": "crm.source"},
		],
		"verbs": [{"verb": "crm.take"}],
	},
	{
		"doctype": "Lead",
		"band": [
			{"label": _lt("Came In"), "source": "Measure", "measure": "crm.came_in"},
			{"label": _lt("First Reply"), "source": "Measure", "measure": "crm.reply"},
			{"label": _lt("Next Step"), "source": "Measure", "measure": "crm.next_step"},
			{"label": _lt("Last Contact"), "source": "Measure", "measure": "crm.contact"},
			{"label": _lt("Deals"), "source": "Measure", "measure": "crm.deals"},
			{"label": _lt("Source"), "source": "Measure", "measure": "crm.source"},
		],
		"verbs": [{"verb": "crm.take"}],
	},
]
