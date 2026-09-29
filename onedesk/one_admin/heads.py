"""What the operator's records say above their fields. See one/head.py.

Every one of these records is read-only, because every field on it is the
record of something that happened (a signup, a call to Frappe Cloud, a
measurement, a rung). So each opens on where it stands, in a word and a
colour; one sentence saying what that means for somebody; for a workspace and
a job, how far along they are; and the verbs that move them, which run the
same code the nightly ladder runs (operator.py).
"""

from urllib.parse import quote

import frappe
from frappe import _, _lt
from frappe.utils import escape_html, flt, get_fullname
from frappe.utils.caching import request_cache

from onedesk.one.heads import size
from onedesk.one_admin import ledger, operator

#: Each rung of a workspace in a word, and its colour.
TENANT = {
	"Requested": ("orange", _lt("Waiting to be built")),
	"Provisioning": ("blue", _lt("Being built")),
	"Live": ("green", _lt("Live")),
	"Overdue": ("orange", _lt("Payment overdue")),
	"Suspended": ("red", _lt("Suspended")),
	"Archived": ("grey", _lt("Archived")),
	"Dropped": ("grey", _lt("Dropped")),
	"Failed": ("red", _lt("Provisioning failed")),
}

JOB = {
	"Pending": ("orange", _lt("Waiting to run")),
	"Waiting": ("blue", _lt("Waiting on Frappe Cloud")),
	"Done": ("green", _lt("Done")),
	"Failed": ("red", _lt("Failed")),
}

#: A signup's state, as its list says it too (account_request_list.js).
REQUEST = {
	"New": ("grey", _lt("Not paid")),
	"Paying": ("orange", _lt("At checkout")),
	"Paid": ("orange", _lt("Paid, not built")),
	"Provisioning": ("blue", _lt("Being built")),
	"Done": ("green", _lt("Built")),
	"Failed": ("red", _lt("Paid, build failed")),
	"Abandoned": ("grey", _lt("Abandoned")),
}

#: A domain's state in the customer's own words (settings.js says the same).
DOMAIN = {
	"Pending": ("orange", _lt("Waiting")),
	"Active": ("green", _lt("Working")),
	"Broken": ("red", _lt("Not working")),
	"Gone": ("grey", _lt("Not at Cloudflare")),
}

MODEL = {
	"Priced": ("green", _lt("Priced")),
	"Needs Review": ("orange", _lt("Needs review")),
	"Withdrawn": ("grey", _lt("Withdrawn")),
}


def _pill(says: dict, state: str | None):
	if not state:
		return None
	colour, word = says.get(state, ("grey", state))
	return {"label": str(word), "colour": colour}


def _number(value, places: int = 2) -> str:
	"""A number as the desk formats one, with its places."""
	return frappe.format(flt(value, places), {"fieldtype": "Float", "precision": places})


def _confirm(text: str, warning: str = "") -> list[dict]:
	"""A verb that is confirmed, saying what it costs rather than "are you
	sure"."""
	html = f"<p>{escape_html(text)}</p>" + (
		f'<p class="text-danger">{escape_html(warning)}</p>' if warning else ""
	)
	return [{"fieldtype": "HTML", "fieldname": "what", "options": html}]


# ------------------------------------------------------------------ a workspace


@request_cache
def _standing(name: str) -> dict:
	return operator.standing(name)


@request_cache
def _credits(name: str) -> dict:
	return operator.credit_standing(name)


def _falling(where: dict) -> bool:
	return where.get("days_left") is not None and bool(where.get("next"))


def tenant_state(doc):
	return None if doc.is_new() else _pill(TENANT, doc.status)


def tenant_address(doc):
	"""Its address, and when it falls a rung: the one the operator is reading
	for while a workspace is falling."""
	if doc.is_new():
		return None
	where = _standing(doc.name)
	said = [doc.get("domain") or doc.get("site") or doc.name]
	if _falling(where):
		below = where["next"]
		rung = _(below)
		said.append(
			_("Falls to {0} tonight.").format(rung)
			if where["days_left"] == 0
			else _("Falls to {0} in {1} days.").format(rung, where["days_left"])
		)
	colour = (
		"red"
		if where.get("days_left") is not None and where["days_left"] <= 2
		else "orange"
		if where.get("owing")
		else "blue"
	)
	return {"text": " · ".join(said), "colour": colour}


def tenant_plan(doc):
	"""The plan it pays for, and how many add-ons on top: what every other
	number in the band is measured against. Opens the plan."""
	if doc.is_new() or not doc.get("offering"):
		return None
	label = frappe.db.get_value("Offering", doc.offering, "label") or doc.offering
	extra = len(doc.get("add_ons") or [])
	return {
		"value": (
			_("{0} + 1 add-on").format(label) if extra == 1 else _("{0} + {1} add-ons").format(label, extra)
		)
		if extra
		else label,
		"route": f"/desk/offering/{quote(doc.offering, safe='')}",
	}


def tenant_storage(doc):
	"""What it stores against what its plan allows: a Long Int of bytes over
	another is arithmetic somebody has to do. Over the limit is in red. With no
	limit written, what it stores on its own."""
	limit, held = flt(doc.get("storage_limit")), flt(doc.get("storage_bytes"))
	if doc.is_new():
		return None
	if limit <= 0:
		return {"value": size(held) if held else "0"}
	return {
		"value": _("{0} of {1}").format(size(held) if held else "0", size(limit)),
		"tone": "alarm" if held > limit else None,
		"meter": {"value": min(held, limit), "of": limit},
	}


def tenant_credits(doc):
	"""What it has left to spend on AI, against the month's spend. Empty when
	it is out: the first thing to see on a workspace that cannot ask anything."""
	if doc.is_new():
		return None
	now = _credits(doc.name)
	used, left = flt(now.get("month_credits")), max(0, flt(now.get("available")))
	whole = used + left
	return [
		{
			"label": _("Credits Left"),
			"value": _number(left) if left > 0 else "0",
			"tone": "alarm" if left <= 0 else "waiting" if whole and used / whole > 0.8 else None,
			"meter": {"value": left, "of": whole} if whole else None,
		},
		{
			"label": _("Used This Month"),
			"value": _("{0} in {1} calls").format(_number(used), now.get("month_calls") or 0),
			"route": f"/desk/query-report/AI Usage?tenant={quote(doc.name, safe='')}&by=Model",
		},
	]


def tenant_rung(doc):
	"""Only while it is falling: a live workspace has no clock running against
	it, and a number at nought would suggest one does."""
	if doc.is_new():
		return None
	where = _standing(doc.name)
	if not _falling(where):
		return None
	left, below = where["days_left"], where["next"]
	days = where.get("days") or left
	return {
		"label": _("Falls to {0}").format(_(below)),
		"value": _("Tonight") if left == 0 else _("In {0} days").format(left),
		"tone": "alarm" if left <= 2 else "waiting",
		"meter": {"value": days - left, "of": days} if days else None,
	}


def _may_fall(doc) -> bool:
	return not doc.is_new() and bool(_standing(doc.name).get("next"))


def _fall_label(doc) -> str:
	where = _standing(doc.name)
	below = where["next"]
	return where.get("verb") or _(below)


def _fall_fields(doc) -> list[dict]:
	where = _standing(doc.name)
	return _confirm(
		_("{0} {1}?").format(_fall_label(doc), doc.get("workspace_name") or doc.name),
		where.get("warning") or "",
	)


# ------------------------------------------------------------------ a job


@request_cache
def _walk(name: str) -> dict:
	return operator.walk(name)


def job_state(doc):
	return None if doc.is_new() else _pill(JOB, _walk(doc.name)["status"])


def job_steps(doc):
	"""Where in its walk it is: a step is a function name on the record, and
	one that stopped says which, because that is what anybody opens it for."""
	if doc.is_new():
		return None
	walk = _walk(doc.name)
	if not walk["of"]:
		return None
	meter = {"value": walk["of"] if walk["status"] == "Done" else walk["at"], "of": walk["of"]}
	if walk["status"] == "Done":
		return {"label": _("Steps"), "value": _("Finished all {0}").format(walk["of"]), "meter": meter}
	now = walk["steps"][walk["at"]] if walk["at"] < len(walk["steps"]) else None
	label = (_("Failed at Step {0} of {1}") if walk["status"] == "Failed" else _("Step {0} of {1}")).format(
		walk["at"] + 1, walk["of"]
	)
	if walk["attempts"] and walk["status"] != "Failed":
		label += " · " + _("Tried {0} times").format(walk["attempts"])
	return {
		"label": label,
		"value": now["said"] if now else _("the start"),
		"tone": "alarm" if walk["status"] == "Failed" else None,
		"meter": meter,
	}


# ------------------------------------------------------------------ a signup


def request_state(doc):
	return None if doc.is_new() else _pill(REQUEST, doc.status)


def request_said(doc):
	"""The one that costs money wins. A paid request with no workspace is
	somebody waiting; a failed one says why, which decides whether building it
	again will work."""
	if doc.is_new():
		return None
	if doc.status == "Failed":
		return {
			"text": _("Paid, and making the workspace stopped: {0}").format(doc.failed_reason)
			if doc.get("failed_reason")
			else _("Paid, and making the workspace stopped before it was created."),
			"colour": "red",
		}
	if doc.status == "Paid" and not doc.get("tenant"):
		return {"text": _("Paid, and no workspace was created. Build it."), "colour": "orange"}
	if doc.status == "Provisioning":
		return {"text": _("The workspace is being built. Its job has the detail."), "colour": "blue"}
	if doc.status == "Abandoned":
		return {
			"text": _("Not paid within {0} days, so its name is free again.").format(signup_days()),
			"colour": "grey",
		}
	return None


def signup_days() -> int:
	from onedesk.one_admin.signup import ABANDONED_DAYS

	return ABANDONED_DAYS


# ------------------------------------------------------------------ a credit


def _n(value) -> str:
	"""Credits to two places, and none when they are whole."""
	said = _number(value)
	return said.rstrip("0").rstrip(".") if "." in said else said


def credit_said(doc):
	"""A grant says what is left of it and until when; a spend, what it came
	out of; one taken back, by whom and why."""
	if doc.is_new() or doc.docstatus != 1:
		return None
	from frappe.utils import formatdate, getdate, today

	if doc.kind == "Grant":
		left = ledger.left_of(doc.name)
		gone = doc.expires_on and getdate(doc.expires_on) < getdate(today())
		taken = ledger.taken_back(doc.name)
		if taken:
			text = _("{0} of its {1} credits were taken back.").format(_n(taken), _n(doc.credits))
		elif left <= 0:
			text = _("All {0} credits of it are used.").format(_n(doc.credits))
		elif gone:
			text = _("It expired on {0} with {1} of {2} credits unused.").format(
				formatdate(doc.expires_on), _n(left), _n(doc.credits)
			)
		elif doc.expires_on:
			text = _("{0} of {1} credits left, until {2}.").format(
				_n(left), _n(doc.credits), formatdate(doc.expires_on)
			)
		else:
			text = _("{0} of {1} credits left, and they never expire.").format(_n(left), _n(doc.credits))
		came = {
			"Plan": _("The plan's monthly credits."),
			"Purchase": _("A credit pack they bought."),
			"Operator": _("Given by {0}.").format(
				get_fullname(doc.reference) if doc.reference else _("an operator")
			),
		}.get(doc.source)
		return {
			"text": f"{text} {came}" if came else text,
			"colour": "grey" if gone or left <= 0 else "green",
		}
	if doc.source == "Operator":
		return {
			"text": _("Taken back by {0}: {1}").format(get_fullname(doc.reference), doc.why or ""),
			"colour": "orange",
		}
	if not doc.against:
		return {"text": _("Spent beyond what the workspace had, so it is owed."), "colour": "orange"}
	grant = ledger.said_of(doc.against)
	return {
		"text": _("Drawn from {0}: {1}").format(doc.against, grant.get("why") or grant.get("source") or ""),
		"colour": "grey",
	}


def _may_take_back(doc) -> bool:
	return (
		doc.docstatus == 1
		and doc.kind == "Grant"
		and doc.source == "Operator"
		and ledger.left_of(doc.name) > 0
	)


def _take_back_fields(doc) -> list[dict]:
	return [
		*_confirm(
			_("Take back the {0} credits left of this?").format(_n(ledger.left_of(doc.name))),
			_("What was already spent from it stays spent."),
		),
		{"fieldtype": "Small Text", "fieldname": "why", "label": _("Why"), "reqd": 1},
	]


# ------------------------------------------------------------------ a domain


def domain_state(doc):
	return None if doc.is_new() else _pill(DOMAIN, doc.status)


def domain_said(doc):
	"""What is true of a name now, and what has to happen for it to work:
	where its CNAME must point, Cloudflare's own words about what stops it,
	and since when. A working name says only whether it is the main one."""
	if doc.is_new():
		return None
	target = frappe.db.get_value("Tenant", doc.tenant, "domain") if doc.tenant else None
	record = _("It needs a CNAME record from {0} to {1}.").format(doc.domain, target) if target else ""
	problem = " " + _("Cloudflare says: {0}").format(doc.problem) if doc.get("problem") else ""
	if doc.status == "Active":
		return {"text": _("The workspace's main address."), "colour": "blue"} if doc.get("is_main") else None
	if doc.status == "Pending":
		since = (
			" " + _("Waiting since {0}.").format(frappe.utils.format_datetime(doc.asked_on, "d MMM yyyy"))
			if doc.get("asked_on")
			else ""
		)
		return {
			"text": (_("Waiting for the customer's DNS.") + " " + record + since + problem).strip(),
			"colour": "orange",
		}
	if doc.status == "Broken":
		return {
			"text": (_("{0} is not working.").format(doc.domain) + " " + record + problem).strip(),
			"colour": "red",
		}
	return {
		"text": _("Cloudflare has no record of {0}. The customer can remove it and add it again.").format(
			doc.domain
		),
		"colour": "grey",
	}


# ------------------------------------------------------------------ an offering


def offering_sold(doc):
	"""Who has it, and what an edit here does to them: the price never
	reaches them, the quotas do the next time they change their plan or
	add-ons (`quota.apply` copies them from here then)."""
	if doc.is_new():
		return None
	if doc.kind == "Credit Pack":
		return {
			"text": _("A pack is bought once and used up. Changing it changes only the next one sold."),
			"colour": "blue",
		}
	count = operator.sold(doc.name)
	if not count["all"]:
		return {"text": _("No workspace has this yet."), "colour": "blue"}
	many = (
		_("One workspace has this")
		if count["all"] == 1
		else _("{0} workspaces have this").format(count["all"])
	)
	on = (
		many
		+ ", "
		+ (_("{0} of them live.").format(count["live"]) if count["live"] else _("none of them live."))
	)
	return {
		"text": on
		+ " "
		+ _(
			"They keep the price they pay. A changed quota reaches them the next time they change their plan or add-ons."
		),
		"colour": "orange",
	}


# ------------------------------------------------------------------ a model


def model_state(doc):
	if doc.is_new():
		return None
	if doc.offered:
		return {"label": _("Offered"), "colour": "green"}
	return _pill(MODEL, doc.status)


def model_markup(doc):
	"""The markup in effect rather than the one on the record: an empty field
	meaning "the default" is a number somebody will read as "none"."""
	if doc.is_new():
		return None
	if doc.status != "Priced":
		return {"text": doc.why, "colour": "orange"} if doc.get("why") else None
	markup = flt(doc.get("markup")) or flt(frappe.db.get_single_value("One Admin Settings", "default_markup"))
	if not markup:
		return {"text": _("No markup is set, so this model cannot be called."), "colour": "red"}
	times = str(int(markup)) if markup.is_integer() else str(markup)
	text = _("Charged at {0}× what the provider charges.").format(times)
	if not flt(doc.get("markup")):
		text += " " + _("From the default.")
	return {"text": text, "colour": "blue"}


MEASURES = {
	"tenant.state": tenant_state,
	"tenant.address": tenant_address,
	"tenant.plan": tenant_plan,
	"tenant.storage": tenant_storage,
	"tenant.credits": tenant_credits,
	"tenant.rung": tenant_rung,
	"job.state": job_state,
	"job.steps": job_steps,
	"request.state": request_state,
	"request.said": request_said,
	"domain.state": domain_state,
	"domain.said": domain_said,
	"offering.sold": offering_sold,
	"credit.said": credit_said,
	"model.state": model_state,
	"model.markup": model_markup,
}

VERBS = {
	# Every fall is confirmed, saying what it costs: Delete Files deletes
	# files, Suspend stops a company working.
	"tenant.fall": {
		"doctypes": ["Tenant"],
		"label": _fall_label,
		"when": _may_fall,
		"fields": _fall_fields,
		"run": lambda doc, **_values: operator.fall(doc.name, _standing(doc.name)["next"]) and None,
	},
	"tenant.restore": {
		"doctypes": ["Tenant"],
		"label": lambda doc: _("Restore"),
		"when": lambda doc: not doc.is_new() and bool(_standing(doc.name).get("may_restore")),
		"run": lambda doc, **_values: operator.restore(doc.name) and None,
	},
	# Under a group: neither is done daily, and both cost a round trip to
	# somebody else's service.
	"tenant.measure": {
		"doctypes": ["Tenant"],
		"label": lambda doc: _("Measure storage"),
		"group": lambda doc: _("Refresh"),
		"when": lambda doc: not doc.is_new(),
		"run": lambda doc, **_values: operator.measure(doc.name) and None,
	},
	"tenant.refresh_domains": {
		"doctypes": ["Tenant"],
		"label": lambda doc: _("Refresh domains"),
		"group": lambda doc: _("Refresh"),
		"when": lambda doc: not doc.is_new(),
		"run": lambda doc, **_values: operator.refresh_domains(doc.name) and None,
	},
	"job.resume": {
		"doctypes": ["Provisioning Job"],
		"label": lambda doc: _("Resume"),
		"when": lambda doc: not doc.is_new() and doc.status == "Failed",
		"fields": lambda doc: _confirm(_("Run {0} again, from the step it stopped on?").format(doc.name)),
		"run": lambda doc, **_values: operator.resume(doc.name) and None,
	},
	# Money taken and nothing given: until this, the only way to finish it was
	# to replay the webhook.
	"request.build": {
		"doctypes": ["Account Request"],
		"label": lambda doc: _("Build Workspace"),
		"when": lambda doc: not doc.is_new() and not doc.get("tenant") and doc.status in ("Paid", "Failed"),
		"fields": lambda doc: _confirm(_("Create {0} for {1} now?").format(doc.slug, doc.email)),
		"run": lambda doc, **_values: operator.retry_signup(doc.name) and None,
	},
	"credit.take_back": {
		"doctypes": [ledger.ENTRY],
		"label": lambda doc: _("Take Back"),
		"when": _may_take_back,
		"fields": _take_back_fields,
		"run": lambda doc, why=None, **_values: operator.take_back_credits(doc.name, why) and None,
	},
	"domain.refresh": {
		"doctypes": ["Tenant Domain"],
		# The customer's own screen and Home both say this.
		"label": lambda doc: _("Check Again"),
		"when": lambda doc: not doc.is_new(),
		"run": lambda doc, **_values: operator.refresh_domain(doc.name) and None,
	},
}

HEADS = [
	{
		"doctype": "Tenant",
		"indicators": [{"label": _lt("Standing"), "measure": "tenant.state"}],
		"sentences": [{"measure": "tenant.address"}],
		"band": [
			{"label": _lt("Plan"), "source": "Measure", "measure": "tenant.plan"},
			{"label": _lt("Storage"), "source": "Measure", "measure": "tenant.storage"},
			{"label": _lt("Credits"), "source": "Measure", "measure": "tenant.credits"},
			{"label": _lt("Falls"), "source": "Measure", "measure": "tenant.rung"},
		],
		"verbs": [
			{"verb": "tenant.fall"},
			{"verb": "tenant.restore", "primary": 1},
			{"verb": "tenant.measure"},
			{"verb": "tenant.refresh_domains"},
		],
	},
	{
		"doctype": "Provisioning Job",
		"indicators": [{"label": _lt("Status"), "measure": "job.state"}],
		"band": [{"label": _lt("Steps"), "source": "Measure", "measure": "job.steps"}],
		"verbs": [{"verb": "job.resume", "primary": 1}],
	},
	{
		"doctype": "Account Request",
		"indicators": [{"label": _lt("Status"), "measure": "request.state"}],
		"sentences": [{"measure": "request.said"}],
		"verbs": [{"verb": "request.build", "primary": 1}],
	},
	{
		"doctype": "Tenant Domain",
		"indicators": [{"label": _lt("Status"), "measure": "domain.state"}],
		"sentences": [{"measure": "domain.said"}],
		"verbs": [{"verb": "domain.refresh", "primary": 1}],
	},
	{
		"doctype": "Offering",
		"sentences": [{"measure": "offering.sold"}],
	},
	{
		"doctype": ledger.ENTRY,
		"sentences": [{"measure": "credit.said"}],
		"verbs": [{"verb": "credit.take_back"}],
	},
	{
		"doctype": "AI Model",
		"indicators": [{"label": _lt("Status"), "measure": "model.state"}],
		"sentences": [{"measure": "model.markup"}],
	},
]
