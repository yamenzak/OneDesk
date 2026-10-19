"""Extensions: code OneAI writes for a workspace, which its administrators
turn on and off but never write or read.
"""

from contextlib import contextmanager

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit

from onedesk.one import roles
from onedesk.one_studio import checks, guard, review, tell, trial

EXTENSION = "Extension"
ON_SCREEN, ON_SERVER = "On Screen", "On Server"

SCRIPTS = {ON_SCREEN: ("Client Script", "enabled"), ON_SERVER: ("Server Script", "disabled")}

PAGE = "Page"

FREQUENCY = {
	"Every Hour": "Hourly",
	"Every Day": "Daily",
	"Every Week": "Weekly",
	"Every Month": "Monthly",
	"Scheduled": "Cron",
}
ON_A_SCHEDULE = "Scheduled"

LEAST_BETWEEN = 60 * 60

PREFIX = "OneStudio "

WRITTEN = (
	"title", "runs", "record_doctype", "view", "place", "event", "cron", "explanation", "asked", "asked_by",
	"review", "review_note", "written_on",
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
	return review.fingerprint(doc.code, doc.runs, doc.record_doctype, _when(doc))


def _when(doc) -> str | None:
	"""Where and when it runs, as the review read it: the event on the
	server, the view on the screen, the page and its event on a page."""
	if doc.runs == ON_SERVER:
		return f"{doc.event} {doc.cron}" if doc.event == ON_A_SCHEDULE and doc.get("cron") else doc.event
	return doc.get("place") if doc.view == PAGE else doc.view


def boot(bootinfo) -> None:
	"""extend_bootinfo: whether this bench runs server extensions, for the
	Extensions list to say Cannot Run Here as the head does; and for
	everybody, the page extensions that are on, which run in their browser as
	a Client Script would (places.js)."""
	from onedesk.one_studio import places

	if roles.administers():
		bootinfo.one_studio_server = runs_server_scripts()
	bootinfo.one_places = places.for_boot()
	bootinfo.one_page_extensions = [
		one
		for one in frappe.get_all(
			EXTENSION,
			filters={"enabled": 1, "runs": ON_SCREEN, "view": PAGE},
			fields=["name", "place", "record_doctype as doctype", "code", "review", "reviewed", "runs", "view"],
			ignore_permissions=True,
		)
		if one.review == "Passed"
		and one.reviewed == review.fingerprint(one.code, one.runs, one.doctype, one.place)
	]
	for one in bootinfo.one_page_extensions:
		for kept in ("review", "reviewed", "runs", "view"):
			one.pop(kept, None)


def since(name: str, days: int) -> object:
	"""Where an extension's errors that are about its present code begin:
	`days` ago, or when OneAI last wrote it if that is later."""
	from frappe.utils import add_days, get_datetime, now_datetime

	start = add_days(now_datetime(), -days)
	written = frappe.db.get_value(EXTENSION, name, "written_on")
	return max(start, get_datetime(written)) if written else start


def cron_refused(cron: str | None) -> str | None:
	"""Why a schedule cannot be kept, or None: a cron line frappe's scheduler
	reads, at most hourly."""
	from croniter import croniter
	from frappe.utils import now_datetime

	if not cron or not croniter.is_valid(cron):
		return _("Say when it runs as a cron line, such as 0 8 * * 1-5 for eight each weekday morning.")
	runs = croniter(cron, now_datetime())
	first, second, third = runs.get_next(float), runs.get_next(float), runs.get_next(float)
	if min(second - first, third - second) < LEAST_BETWEEN:
		return _("A scheduled extension runs at most once an hour.")
	return None


def check(
	runs: str,
	doctype: str,
	view: str | None,
	event: str | None,
	code: str,
	place: str | None = None,
	cron: str | None = None,
) -> None:
	"""Refuse what no extension may be, before anything is kept."""
	if runs not in SCRIPTS:
		raise guard.Refused(_("An extension runs on the screen or on the server."))
	if runs == ON_SCREEN and view == PAGE:
		from onedesk.one_studio import places

		found = places.place_of(place)
		if not found:
			raise guard.Refused(_("{0} is not a page an extension can run on.").format(place))
		page = places.PLACES[found[0]]
		named = None if page["record"] else doctype
		guard.on_page(code, page["label"], set(page["events"]), named, site())
		checks.length(code)
		trial.parsed(code)
		return
	if runs == ON_SCREEN and view not in guard.VIEWS:
		raise guard.Refused(_("An extension on the screen runs on a form, a list or one of One's pages."))
	if runs == ON_SERVER and event not in guard.EVENTS + guard.SCHEDULED:
		raise guard.Refused(
			_(
				"An extension on the server runs when a record is saved, submitted, cancelled or deleted, "
				"or on a schedule."
			)
		)
	if event == ON_A_SCHEDULE and (refused := cron_refused(cron)):
		raise guard.Refused(refused)
	known = site()
	if runs == ON_SERVER:
		guard.on_server(code, doctype, known, event)
		checks.on_server(code, None if event in guard.SCHEDULED else doctype, fields_of)
	else:
		guard.on_screen(code, doctype, known)
		checks.on_screen(code, doctype, view, fields_of)
		trial.parsed(code)


def fields_of(doctype: str | None) -> set | None:
	"""The field names a kind of record has, for checks.py; None for a kind
	there is not."""
	if not doctype or not frappe.db.exists("DocType", doctype):
		return None
	return {one.fieldname for one in frappe.get_meta(doctype).fields if one.fieldname}


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
	place: str | None = None,
	cron: str | None = None,
) -> dict:
	"""Keep an extension OneAI wrote, off, with its review: a new one, or a
	new version of `extension`. Refuses what guard.py refuses."""
	from onedesk.one_studio import places

	roles.require()
	paged = runs == ON_SCREEN and (view == PAGE or bool(place))
	if paged:
		view = PAGE
		doctype = places.doctype_for(place, doctype)
		if not doctype:
			raise guard.Refused(_("Say which kind of record's head it runs on."))
	cron = (cron or "").strip() if event == ON_A_SCHEDULE else None
	check(runs, doctype, view, event, code, place, cron)
	tried = trial.ran(code, doctype, event) if runs == ON_SERVER else ""
	when = place if paged else (f"{event} {cron}" if cron else (event or view))
	said = review.ask(runs, doctype, when, explanation, code)
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
			"place": place if paged else None,
			"event": event if runs == ON_SERVER else None,
			"cron": cron,
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
	doc.flags.ignore_permissions = True
	doc.flags.written = True
	doc.save()
	return {"extension": doc.name, "review": doc.review, "why": doc.review_note, "tried": tried}


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
	match. A page extension has none: it runs from the extension itself."""
	if doc.runs == ON_SCREEN and doc.view == PAGE:
		with _as_administrator():
			for kind, _field in SCRIPTS.values():
				if doc.script and frappe.db.exists(kind, doc.script):
					frappe.delete_doc(kind, doc.script, ignore_permissions=True, force=True)
		if doc.script:
			doc.db_set("script", None, update_modified=False)
		_heard(doc)
		return
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
		elif doc.event in guard.SCHEDULED:
			script.update(
				{
					"script_type": "Scheduler Event",
					"reference_doctype": None,
					"doctype_event": None,
					"event_frequency": FREQUENCY[doc.event],
					"cron_format": doc.cron if doc.event == ON_A_SCHEDULE else None,
					"script": guard.wrapped(doc.name, doc.code, scheduled=True),
					"disabled": int(not doc.enabled),
					"allow_guest": 0,
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
	_heard(doc)


def _heard(doc) -> None:
	"""Turned on or off by a person, the other administrators hear."""
	before = doc.get_doc_before_save()
	if before and before.enabled != doc.enabled and not doc.flags.written:
		if doc.enabled:
			tell.extension_turned_on(_told(doc))
		else:
			tell.extension_turned_off(_told(doc))
	frappe.publish_realtime("list_update", {"doctype": EXTENSION, "name": doc.name}, after_commit=True)


def _told(doc, link: bool = True) -> dict:
	"""What the other administrators hear of an extension turned on, off or
	deleted (notifications/one_studio/): from that moment it runs on everybody's work,
	or no longer does."""
	when = _place_said(doc) if doc.view == PAGE else _when(doc)
	return {
		"link": f"/desk/extension/{doc.name}" if link else None,
		"who": frappe.utils.get_fullname(frappe.session.user),
		"title": doc.title,
		"where": _("{0}, {1}").format(_(doc.runs), _(when) if when else ""),
		"kind": _(doc.record_doctype),
		"explanation": doc.explanation or "",
	}


def _place_said(doc) -> str:
	"""A page extension's place as a person reads it: OneMail, a conversation
	opened."""
	from onedesk.one_studio import places

	found = places.place_of(doc.get("place"))
	if not found:
		return doc.get("place") or ""
	page, event = found
	label = places.PLACES[page]["label"]
	about = places.PLACES[page]["events"][event]["about"]
	return _("{0}: {1}").format(_(label), _(about))


def remove(doc, method=None) -> None:
	"""Extension on_trash: frappe's script goes with it, and the other
	administrators hear of it."""
	tell.extension_deleted(_told(doc, link=False))
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
	said = "\n".join(filter(None, [(message or "")[:500], (stack or "")[:2000]]))
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
	tell.extensions_failing(people, ", ".join(said))
