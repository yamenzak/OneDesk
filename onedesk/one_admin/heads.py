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
from frappe.utils import escape_html, flt
from frappe.utils.caching import request_cache

from onedesk.one.heads import size
from onedesk.one_admin import operator

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
	"Failed": ("red", _lt("Stopped")),
}

REQUEST = {
	"New": ("grey", _lt("Not paid")),
	"Paying": ("orange", _lt("At checkout")),
	"Paid": ("orange", _lt("Paid, not built")),
	"Provisioning": ("blue", _lt("Being set up")),
	"Done": ("green", _lt("Done")),
	"Failed": ("red", _lt("Stopped")),
}

DOMAIN = {
	"Pending": ("orange", _lt("Waiting")),
	"In Progress": ("blue", _lt("Being set up")),
	"Active": ("green", _lt("Active")),
	"Broken": ("red", _lt("Not working")),
	"Gone": ("grey", _lt("Removed")),
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


def tenant_storage(doc):
	"""What it stores against what its plan allows: a Long Int of bytes over
	another is arithmetic somebody has to do. Over the limit is in red."""
	limit, held = flt(doc.get("storage_limit")), flt(doc.get("storage_bytes"))
	if doc.is_new() or limit <= 0:
		return None
	return {
		"value": _("{0} of {1}").format(size(held), size(limit)),
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
			"value": _number(left) if left > 0 else _("None"),
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
	label = (_("Stopped at Step {0} of {1}") if walk["status"] == "Failed" else _("Step {0} of {1}")).format(
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
			"text": _("Stopped: {0}").format(doc.failed_reason)
			if doc.get("failed_reason")
			else _("Stopped before the workspace was created."),
			"colour": "red",
		}
	if doc.status == "Paid" and not doc.get("tenant"):
		return {"text": _("Paid, and no workspace was created. Build it."), "colour": "orange"}
	if doc.status == "Provisioning":
		return {"text": _("The workspace is being set up. Its job has the detail."), "colour": "blue"}
	return None


# ------------------------------------------------------------------ a domain


def domain_state(doc):
	return None if doc.is_new() else _pill(DOMAIN, doc.status)


def domain_said(doc):
	"""Why a name is not working yet, of which there are three answers: nobody
	has asked Frappe Cloud, it is working on it, or the DNS does not point
	here."""
	said = {
		"Broken": (
			"red",
			_("{0} does not point to this workspace. The customer has to change their DNS."),
		),
		"Gone": ("grey", _("Frappe Cloud no longer has this domain.")),
		"In Progress": ("blue", _("Frappe Cloud is issuing the certificate. This takes a few minutes.")),
		"Pending": ("orange", _("Asked for, and Frappe Cloud has not answered yet.")),
	}.get(doc.status)
	if doc.is_new() or not said:
		return None
	colour, text = said
	return {"text": text.format(doc.domain), "colour": colour}


# ------------------------------------------------------------------ an offering


def offering_sold(doc):
	"""How many workspaces already bought it: quotas are copied onto a
	workspace when it signs up, so an edit here changes nothing for them."""
	if doc.is_new():
		return None
	count = operator.sold(doc.name)
	if not count["all"]:
		return {"text": _("No workspace has bought this yet."), "colour": "blue"}
	many = (
		_("One workspace bought this")
		if count["all"] == 1
		else _("{0} workspaces bought this").format(count["all"])
	)
	on = (
		many + ", " + _("{0} of them live.").format(count["live"])
		if count["live"]
		else many + ", " + _("none of them live.")
	)
	return {
		"text": on + " " + _("Changing a price or a quota here does not change theirs."),
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
	"domain.refresh": {
		"doctypes": ["Tenant Domain"],
		"label": lambda doc: _("Refresh"),
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
		"doctype": "AI Model",
		"indicators": [{"label": _lt("Status"), "measure": "model.state"}],
		"sentences": [{"measure": "model.markup"}],
	},
]
