"""Extensions: code OneAI writes for a workspace, which its administrators
turn on and off but never write or read.

An extension is one record of ours, **Extension**, and one of frappe's: a
Client Script for one that runs on the screen, a Server Script on a record
event for one that runs on the server. Ours holds what the administrator
reads (the title, what it does, what was asked and the review) and, at a
level only frappe's System Manager reads, the code; frappe's is made from it
here, as Administrator, since frappe keeps both to its own managers, and is
nobody else's to change.

- **Written only by OneAI** (`write`, called by its tool in ai.py), after
  guard.py has read the code and review.py has had a second model read it
  against what it says it does. Nothing it writes is on until somebody turns
  it on.
- **On only as reviewed.** An extension turns on only if its review passed
  and its code, record, view and event are the ones that passed
  (`reviewed_as`). Nothing OneAI wrote changes by hand (`WRITTEN`). One on the server turns on only
  where the bench runs server scripts at all.
- **Off and deleted by the administrator.** Off disables frappe's script;
  deleting the extension deletes it.
- **An error does not stop the work.** Every extension runs wrapped
  (guard.wrapped on the server, guard.wrapped_on_screen in the browser): what
  it means to stop a save with still stops it, and anything else it trips on
  is written to the error log under its name (in the browser through
  `tripped`) and the work goes on. `failing` tells the administrators each
  morning.
"""

from contextlib import contextmanager

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit

from onedesk.one import roles
from onedesk.one_studio import guard, review

EXTENSION = "Extension"
ON_SCREEN, ON_SERVER = "On Screen", "On Server"

#: frappe's script each kind of extension is, and the field that turns it off.
SCRIPTS = {ON_SCREEN: ("Client Script", "enabled"), ON_SERVER: ("Server Script", "disabled")}

#: frappe's scripts made from extensions are named after them.
PREFIX = "OneStudio "

#: What OneAI writes and the review reads. `read_only` keeps these only in the
#: form, so validate keeps them on the server: an administrator turns an
#: extension on and off, and nothing else.
WRITTEN = (
	"title", "runs", "record_doctype", "view", "event", "explanation", "asked", "asked_by", "review",
	"review_note", "written_on",
)  # fmt: skip


@contextmanager
def _as_administrator():
	"""frappe keeps its scripts to its own managers (Server Script's validate
	calls `only_for`), so ours are written as Administrator, then the request
	gets its own session back."""
	session = frappe.local.session
	held = dict(session)
	frappe.set_user("Administrator")
	frappe.flags.one_studio = True
	try:
		yield
	finally:
		frappe.flags.one_studio = False
		session.clear()
		session.update(held)
		frappe.local.role_permissions = {}
		frappe.local.user_perms = None


def site() -> guard.Site:
	"""What the guard knows of the reader: the kinds they may open, and the
	fields they may not read on each."""
	from onedesk.one import audit

	kinds = set(audit.kinds())
	return guard.Site(
		kinds=kinds,
		unseen={doctype: audit._unseen(doctype) for doctype in kinds},
		doctypes=set(frappe.get_all("DocType", pluck="name")),
	)


def runs_server_scripts() -> bool:
	from frappe.utils.safe_exec import is_safe_exec_enabled

	return is_safe_exec_enabled()


def reviewed_as(doc) -> str:
	"""The fingerprint of an extension as it stands: its code, and where and
	when it runs."""
	when = doc.event if doc.runs == ON_SERVER else doc.view
	return review.fingerprint(doc.code, doc.runs, doc.record_doctype, when)


def boot(bootinfo) -> None:
	"""extend_bootinfo: whether this bench runs server extensions, for the
	Extensions list to say Cannot Run Here as the head does."""
	if roles.administers():
		bootinfo.one_studio_server = runs_server_scripts()


def since(name: str, days: int) -> object:
	"""Where an extension's errors that are about its present code begin:
	`days` ago, or when OneAI last wrote it if that is later."""
	from frappe.utils import add_days, get_datetime, now_datetime

	start = add_days(now_datetime(), -days)
	written = frappe.db.get_value(EXTENSION, name, "written_on")
	return max(start, get_datetime(written)) if written else start


def check(runs: str, doctype: str, view: str | None, event: str | None, code: str) -> None:
	"""Refuse what no extension may be, before anything is kept."""
	if runs not in SCRIPTS:
		raise guard.Refused(_("An extension runs on the screen or on the server."))
	if runs == ON_SCREEN and view not in guard.VIEWS:
		raise guard.Refused(_("An extension on the screen runs on a form or a list."))
	if runs == ON_SERVER and event not in guard.EVENTS:
		raise guard.Refused(
			_("An extension on the server runs when a record is saved, submitted, cancelled or deleted.")
		)
	known = site()
	if runs == ON_SERVER:
		guard.on_server(code, doctype, known, event)
	else:
		guard.on_screen(code, doctype, known)


def write(
	title: str,
	runs: str,
	doctype: str,
	explanation: str,
	code: str,
	asked: str,
	view: str | None = None,
	event: str | None = None,
	extension: str | None = None,
) -> dict:
	"""Keep an extension OneAI wrote, off, with its review: a new one, or a
	new version of `extension`. Refuses what guard.py refuses."""
	roles.require()
	check(runs, doctype, view, event, code)
	said = review.ask(runs, doctype, event or view, explanation, code)
	doc = frappe.get_doc(EXTENSION, extension) if extension else frappe.new_doc(EXTENSION)
	if extension:
		doc.check_permission("write")
	passed = said["verdict"] == "Pass"
	doc.update(
		{
			"title": title,
			"runs": runs,
			"record_doctype": doctype,
			"view": view if runs == ON_SCREEN else None,
			"event": event if runs == ON_SERVER else None,
			"explanation": explanation,
			"asked": asked,
			"asked_by": frappe.session.user,
			"enabled": 0,
			"code": code,
			"review": "Passed" if passed else "Refused",
			"review_note": said["why"],
		}
	)
	doc.reviewed = reviewed_as(doc) if passed else None
	doc.written_on = frappe.utils.now_datetime()
	# The code is above the administrator's level, so frappe would drop it.
	doc.flags.ignore_permissions = True
	doc.flags.written = True
	doc.save()
	return {"extension": doc.name, "review": doc.review, "why": doc.review_note}


def validate(doc, method=None) -> None:
	"""Extension validate: written only by OneAI, on only as reviewed, and
	only where it can run."""
	if not doc.flags.written and (doc.is_new() or any(doc.has_value_changed(f) for f in WRITTEN)):
		frappe.throw(
			_("Only OneAI writes an extension. Ask it to change this one; turning it on or off is yours.")
		)
	if not doc.enabled:
		return
	if doc.review != "Passed" or doc.reviewed != reviewed_as(doc):
		frappe.throw(
			_("This extension has not passed its review, so it cannot be turned on. Ask OneAI to change it.")
		)
	if doc.runs == ON_SERVER and not runs_server_scripts():
		frappe.throw(_("This workspace does not run extensions on the server yet. Ask us to turn them on."))


def sync(doc, method=None) -> None:
	"""Extension on_update: frappe's script made, changed, or turned off to
	match."""
	doctype, _switch = SCRIPTS[doc.runs]
	name = doc.script or f"{PREFIX}{doc.name}"
	other = next(kind for kind, _field in SCRIPTS.values() if kind != doctype)
	with _as_administrator():
		if frappe.db.exists(other, name):
			frappe.delete_doc(other, name, ignore_permissions=True, force=True)
		script = frappe.get_doc(doctype, name) if frappe.db.exists(doctype, name) else frappe.new_doc(doctype)
		if doctype == "Client Script":
			script.update(
				{
					"dt": doc.record_doctype,
					"view": doc.view or "Form",
					"script": guard.wrapped_on_screen(doc.name, doc.code),
					"enabled": int(doc.enabled),
				}
			)
		else:
			script.update(
				{
					"script_type": "DocType Event",
					"reference_doctype": doc.record_doctype,
					"doctype_event": doc.event,
					"script": guard.wrapped(doc.name, doc.code),
					"disabled": int(not doc.enabled),
					"allow_guest": 0,
				}
			)
		if script.is_new():
			script.insert(ignore_permissions=True, set_name=name)
		else:
			script.save(ignore_permissions=True)
	if doc.script != name:
		doc.db_set("script", name, update_modified=False)
	before = doc.get_doc_before_save()
	# Written again by OneAI, it is off until somebody turns it on, which is
	# when the others hear.
	if before and before.enabled != doc.enabled and not doc.flags.written:
		from onedesk.one import notify

		if doc.enabled:
			notify.notify("Extension Turned On", roles.administrators(), **_told(doc))
		else:
			notify.notify("Extension Turned Off", roles.administrators(), **_told(doc))
	frappe.publish_realtime("list_update", {"doctype": EXTENSION, "name": doc.name}, after_commit=True)


def _told(doc, link: bool = True) -> dict:
	"""What the other administrators hear of an extension turned on, off or
	deleted (notifications.py): from that moment it runs on everybody's work,
	or no longer does."""
	when = doc.event if doc.runs == ON_SERVER else doc.view
	return {
		"link": f"/desk/extension/{doc.name}" if link else None,
		"who": frappe.utils.get_fullname(frappe.session.user),
		"title": doc.title,
		"where": _("{0}, {1}").format(_(doc.runs), _(when) if when else ""),
		"kind": _(doc.record_doctype),
		"explanation": doc.explanation or "",
	}


def remove(doc, method=None) -> None:
	"""Extension on_trash: frappe's script goes with it, and the other
	administrators hear of it."""
	from onedesk.one import notify

	notify.notify("Extension Deleted", roles.administrators(), **_told(doc, link=False))
	with _as_administrator():
		for doctype, _field in SCRIPTS.values():
			if doc.script and frappe.db.exists(doctype, doc.script):
				frappe.delete_doc(doctype, doc.script, ignore_permissions=True, force=True)


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=30, seconds=60 * 60)
def tripped(
	extension: str, message: str | None = None, stack: str | None = None, record: str | None = None
) -> None:
	"""A screen extension ran into an error in somebody's browser
	(guard.WRAPPED_ON_SCREEN): written down under its name, as a server one's
	is, for its Errors tab, its count and `failing`. Anybody who opens the form runs
	it, so anybody signed in may say so, and only of an extension that is on
	and on the screen."""
	if frappe.session.user == "Guest":
		raise frappe.PermissionError
	runs, enabled, doctype = frappe.db.get_value(
		EXTENSION, extension, ["runs", "enabled", "record_doctype"]
	) or (None, 0, None)
	if runs != ON_SCREEN or not enabled:
		return
	# The message first, which is what the Errors tab shows; the browser's
	# stack after it, for mending.
	said = "\n".join(filter(None, [(message or "")[:500], (stack or "")[:2000]]))
	# Which record it was open on, if that is one: the Errors tab links to it.
	named = record if record and frappe.db.exists(doctype, record) else None
	frappe.log_error(
		title=f"{guard.TITLE}{extension}",
		message=said,
		reference_doctype=doctype if named else None,
		reference_name=named,
	)


def failing() -> None:
	"""Daily: the extensions that tripped yesterday, told to the
	administrators. Not sent when none did."""
	from frappe.utils import add_days, now_datetime

	from onedesk.one import notify

	since = add_days(now_datetime(), -1)
	rows = frappe.get_all(
		"Error Log",
		filters={"method": ["like", f"{guard.TITLE}%"], "creation": [">=", since]},
		fields=["method", {"COUNT": "*", "as": "times"}],
		group_by="method",
		order_by="times desc",
	)
	if not rows:
		return
	people = roles.administrators()
	if not people:
		return
	said = []
	for one in rows[:10]:
		name = one.method[len(guard.TITLE) :]
		title = frappe.db.get_value(EXTENSION, name, "title") or name
		said.append(_("{0} ({1})").format(title, one.times))
	notify.notify(
		"Extensions Failing",
		people,
		link="/desk/extension?enabled=1",
		sender="Administrator",
		extensions=", ".join(said),
	)
