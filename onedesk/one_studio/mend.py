"""Mending an extension from the errors it ran into: a separate AI action
(`studio_mend`), made here on the server, whose diagnosis is all the chat hears.
"""

import frappe
from frappe import _, _lt

from onedesk.one import registry, roles
from onedesk.one_studio import extensions, guard

MEND = "studio_mend"

TABS = [{"name": "errors", "label": _lt("Errors"), "order": 85, "doctypes": ("Extension",)}]

ERRORS, EACH = 5, 3000


def errors(name: str, days: int = 14, limit: int = 50) -> list[dict]:
	"""An extension's errors since it was last written, at most `days` back,
	newest first: when, on which record, and what went wrong in one line,
	never the code. What the Errors tab shows and
	what OneAI reads (ai.extension_mistakes)."""
	rows = frappe.get_all(
		"Error Log",
		filters={"method": f"{guard.TITLE}{name}", "creation": [">=", extensions.since(name, days)]},
		fields=["creation", "reference_doctype", "reference_name", "error"],
		order_by="creation desc",
		limit=limit,
	)
	return [
		{
			"on": str(row.creation),
			"record_doctype": row.reference_doctype,
			"record_name": row.reference_name,
			"what": what_went_wrong(row.error),
		}
		for row in rows
	]


def what_went_wrong(error: str | None) -> str | None:
	"""The line of an error a person can read. A server error's last line is
	what went wrong; the lines above it are where, and may quote the code. A
	screen error is its message, then the browser's stack. Pure."""
	lines = [line.strip() for line in (error or "").strip().splitlines() if line.strip()]
	if not lines:
		return None
	said = lines[-1] if lines[0].startswith("Traceback") else lines[0]
	return said[:300]


def prompt(doc, errors: list[str], problem: str | None = None) -> str:
	"""What the mender is shown. Pure but for the document it reads."""
	when = doc.event if doc.runs == extensions.ON_SERVER else doc.view
	header = (
		"two lines (a comment and `try:`) and one indent"
		if doc.runs == extensions.ON_SERVER
		else "the wrapper that gives it its own frappe"
	)
	return (
		f"Where it runs: {doc.runs}, {when}, on {doc.record_doctype}.\n\n"
		f"What the administrator is told it does:\n{doc.explanation or ''}\n\n"
		f"The code:\n{doc.code or ''}\n\n"
		+ (f"What the administrator says goes wrong:\n{problem}\n\n" if problem else "")
		+ (
			f"Its latest errors. Each was caught: the record still saved, or the form went on working. "
			f"Line numbers count {header} added before the code:\n\n" + "\n\n---\n\n".join(errors)
			if errors
			else "It has logged no errors."
		)
	)


@frappe.whitelist(methods=["POST"])
def mend(extension: str, problem: str | None = None) -> dict:
	"""Ask the mender what went wrong with an extension and have it mended,
	kept off. Answers the diagnosis, and whether the mended version passed its
	review; never the code. `problem` is what the person says it does wrong,
	for an extension that fails without an error: one that never does its
	work logs nothing."""
	from onedesk.one_ai import run
	from onedesk.one_hr.hiring import read

	roles.require()
	doc = frappe.get_doc(extensions.EXTENSION, extension)
	doc.check_permission("read")
	logged = frappe.get_all(
		"Error Log",
		filters={"method": f"{guard.TITLE}{doc.name}", "creation": [">=", extensions.since(doc.name, 14)]},
		pluck="error",
		order_by="creation desc",
		limit=ERRORS,
	)
	problem = (problem or "").strip()[:EACH]
	if not logged and not problem:
		frappe.throw(_("{0} has run into no errors, so there is nothing to fix.").format(doc.title))
	said = read(run.once(MEND, prompt(doc, [(one or "")[-EACH:] for one in logged], problem))) or {}
	diagnosis = str(said.get("diagnosis") or "").strip()[:600]
	code = str(said.get("code") or "").strip()
	if not diagnosis or not code:
		frappe.throw(
			_("{1} could not work out what went wrong with {0}. Try again later.").format(doc.title, registry.name("one_ai"))
		)
	if code == (doc.code or "").strip():
		frappe.throw(_("{2} could not fix {0}: {1}").format(doc.title, diagnosis, registry.name("one_ai")))
	asked = "\n\n".join(filter(None, [doc.asked, _("Fixed: {0}").format(diagnosis)]))
	try:
		kept = extensions.write(
			title=doc.title,
			runs=doc.runs,
			doctype=doc.record_doctype,
			explanation=str(said.get("explanation") or doc.explanation or "").strip(),
			code=code,
			asked=asked,
			view=doc.view,
			event=doc.event,
			extension=doc.name,
			place=doc.get("place"),
			cron=doc.get("cron"),
		)
	except guard.Refused as refused:
		frappe.throw(_("{1}'s fixed version was not kept: {0}").format(refused, registry.name("one_ai")))
	return {
		"extension": doc.name,
		"diagnosis": diagnosis,
		"review": kept["review"],
		"why": kept["why"],
		"draft": kept.get("draft", False),
	}


@frappe.whitelist()
def listed(extension: str) -> list[dict]:
	"""The Errors tab of an extension: its errors in the last two weeks."""
	roles.require()
	frappe.get_doc(extensions.EXTENSION, extension).check_permission("read")
	return errors(extension)


def start(doc, problem: str | None = None) -> str:
	"""The Fix With OneAI button, and OneAI asked to fix one: mending reads
	and writes with two model calls, close to a minute, so it is a job, and the
	person who asked is told when it is done."""
	roles.require()
	frappe.enqueue(
		"onedesk.one_studio.mend.in_background",
		queue="long",
		timeout=900,
		job_id=f"onestudio-mend-{doc.name}",
		deduplicate=True,
		enqueue_after_commit=True,
		extension=doc.name,
		told=frappe.session.user,
		problem=problem,
	)
	return _("{0} is fixing it. It takes a few minutes; you will be told when it is done.").format(registry.name("one_ai"))


def in_background(extension: str, told: str, problem: str | None = None) -> None:
	"""The job behind the button, run as whoever pressed it."""
	title = frappe.db.get_value(extensions.EXTENSION, extension, "title") or extension
	try:
		said = mend(extension, problem)
	except frappe.ValidationError as e:
		frappe.clear_last_message()
		message, indicator = str(e), "red"
	else:
		if said["review"] == "Passed" and said.get("draft"):
			message = _("{0} The fixed version is on its page; the one that is on keeps running until you use it.").format(
				said["diagnosis"]
			)
			indicator = "green"
		elif said["review"] == "Passed":
			message = _("{0} The fixed version is off until you turn it on.").format(said["diagnosis"])
			indicator = "green"
		else:
			message = _("{0} The fixed version was kept off: the review refused it. {1}").format(
				said["diagnosis"], said["why"]
			)
			indicator = "orange"
	frappe.publish_realtime(
		"msgprint",
		{"title": _("Fixing {0}").format(title), "message": message, "indicator": indicator},
		user=told,
		after_commit=True,
	)
	from onedesk.one_studio import tell

	tell.extension_fixed(told, extension, title, message)
