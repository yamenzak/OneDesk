"""Webhooks: tell another system when a record is made or changed, for a
workspace's administrators. docs/DESK-COVERAGE.md, P2 Integrations.

A webhook is frappe's own Webhook: a kind of record, an event, an address,
and what to send. The workspace administrator is given it and its Webhook
Request Log, and both are in One's sidebar, so the list and form keep One's
rail. Zapier, Make, n8n or the customer's own server take it from there.

Frappe trusts whoever writes one, because only its System Managers may. A
webhook written by somebody frappe does not let customize (layer.held) is
held to what an automation is held to (one/automations.py):

- it is on a kind of record they can open, never frappe's own or One's;
- it sends only fields they may read: a salary above their level is not
  theirs to send somewhere else;
- what it sends names a field of the record, `{{ doc.customer_name }}`, and
  nothing else, and it decides by no code: a webhook that sends only some
  records is an automation with a Call Webhook step;
- it goes over https to a public address, fixed when saved: never a
  template, never the cloud's metadata service or a neighbour.

**The address is checked when it is sent, too.** frappe's plain sender
follows redirects and resolves the name only when it calls, so a public
address could hand the call to an internal one. `install`, run before
every request and job, sends through frappe's own guarded sender from its
automation engine instead, which checks each hop.

Every call is in the Webhook Request Log: what was sent, what came back,
and whether it was delivered, failed and will be tried again, or gave up.
The administrators hear each morning of any that gave up the day before.
"""

import re
from urllib.parse import urlparse

import frappe
from frappe import _

from onedesk.one import layer, roles
from onedesk.one.customize import REFUSED_MODULES

WEBHOOK = "Webhook"
LOG = "Webhook Request Log"

GRANTS = {WEBHOOK: ("read", "write", "create", "delete"), LOG: ("read", "report")}

#: A Jinja tag, and the one kind a workspace's webhook may hold.
TAG = re.compile(r"\{\{.*?\}\}|\{%.*?%\}", re.S)
FIELD = re.compile(r"\{\{-?\s*doc\.([A-Za-z_][A-Za-z0-9_]*)\s*-?\}\}")

#: How long a call may take, and how often it is tried again, at most.
LONGEST = 30
TRIES = 5


def settle() -> None:
	roles.grant(GRANTS)


def install() -> None:
	"""before_request and before_job: frappe's webhook sender, guarded. The
	guarded one checks every address it is sent to, redirects included, and
	refuses any off the public internet."""
	from frappe.automation_engine.actions.core import _send_guarded_request
	from frappe.integrations.doctype.webhook import webhook

	if getattr(webhook.send_webhook_request, "one_guarded", False):
		return

	def guarded(method, url, headers, data, timeout):
		return _send_guarded_request(method, url, headers, data, timeout or 5)

	guarded.one_guarded = True
	webhook.send_webhook_request = guarded


def _kinds() -> list[str]:
	from onedesk.one import audit

	return audit.kinds()


def _check_address(url: str) -> None:
	from frappe.automation_engine.actions.core import AutomationParamError, _guard_url

	url = (url or "").strip()
	if urlparse(url).scheme != "https":
		frappe.throw(_("A webhook is sent over https."))
	try:
		_guard_url(url)
	except AutomationParamError as refused:
		frappe.throw(str(refused))


def validate(doc, method=None) -> None:
	"""Webhook validate: what a webhook written by the workspace may do."""
	if not layer.held():
		return
	doctype = doc.webhook_doctype
	if not doctype or doctype not in _kinds():
		frappe.throw(_("A webhook can only be on a record type you can open."))
	if frappe.get_meta(doctype).module in REFUSED_MODULES:
		frappe.throw(_("{0} can't be sent by a webhook.").format(_(doctype)))
	if (doc.condition or "").strip():
		frappe.throw(
			_(
				"A webhook here sends every record. To send only some, use an automation with a Call Webhook step."
			)
		)
	doc.is_dynamic_url = 0
	doc.background_jobs_queue = None
	doc.timeout = min(int(doc.timeout or 5), LONGEST)
	doc.max_retries = min(int(doc.max_retries or 0), TRIES)
	_check_address(doc.request_url)
	from onedesk.one.audit import _unseen

	unseen = _unseen(doctype)
	sent = [row.fieldname for row in doc.webhook_data or []]
	template = doc.webhook_json or ""
	for tag in TAG.findall(template):
		found = FIELD.fullmatch(tag)
		if not found:
			frappe.throw(
				_("What a webhook sends names a field of the record, such as {0}, and nothing else.").format(
					"{{ doc.name }}"
				)
			)
		sent.append(found.group(1))
	hidden = sorted({one for one in sent if one in unseen})
	if hidden:
		frappe.throw(
			_("You may not read {0}, so a webhook of yours cannot send it.").format(", ".join(hidden))
		)


def _free(user: str) -> bool:
	"""Whoever frappe itself lets customize: held to nothing here."""
	return user == "Administrator" or frappe.has_permission("Custom Field", "write", user=user)


def has_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
	"""Webhook and its log: an administrator's, on the kinds they may read."""
	user = user or frappe.session.user
	if _free(user):
		return True
	if not roles.administers(user):
		return False
	if doc.doctype == LOG:
		if ptype not in ("read", "report", None):
			return False
		doctype = frappe.db.get_value(WEBHOOK, doc.webhook, "webhook_doctype") if doc.webhook else None
		return bool(doctype) and doctype in _kinds()
	return not doc.webhook_doctype or doc.webhook_doctype in _kinds()


def _in(column: str, values) -> str:
	listed = ", ".join(frappe.db.escape(one) for one in values) or "''"
	return f"{column} in ({listed})"


def query(user: str | None = None) -> str | None:
	user = user or frappe.session.user
	if _free(user):
		return None
	if not roles.administers(user):
		return "1=0"
	return _in("`tabWebhook`.`webhook_doctype`", _kinds())


def log_query(user: str | None = None) -> str | None:
	user = user or frappe.session.user
	if _free(user):
		return None
	if not roles.administers(user):
		return "1=0"
	return f"`tabWebhook Request Log`.`webhook` in (select `name` from `tabWebhook` where {_in('`webhook_doctype`', _kinds())})"


def failing() -> None:
	"""Daily: the webhooks whose calls gave up yesterday, told to the
	administrators. Not sent when none did."""
	from frappe.utils import add_days, now_datetime

	from onedesk.one import notify
	from onedesk.one.account import _administrators

	since = add_days(now_datetime(), -1)
	rows = frappe.get_all(
		LOG,
		filters={"status": "Exhausted", "modified": [">=", since]},
		fields=["webhook", {"COUNT": "*", "as": "calls"}],
		group_by="webhook",
		order_by="calls desc",
	)
	if not rows:
		return
	people = _administrators()
	if not people:
		return
	said = ", ".join(_("{0} ({1})").format(one.webhook, one.calls) for one in rows[:10])
	notify.notify(
		"Webhooks Failing",
		people,
		link="/desk/webhook-request-log?status=Exhausted",
		sender="Administrator",
		webhooks=said,
	)
