"""Mending an extension from the errors it ran into.

An administrator never reads an extension's code, so they cannot read why it
fails either: the errors frappe keeps are about the code, line by line. So the
mending is a separate call, its own AI action (`studio_mend`), made here on
the server: shown where the extension runs, what it says it does, its code
and its last errors, and asked what went wrong, in words for somebody who
does not read code, and for the code mended. Nothing of the chat reaches it,
and nothing it is shown goes back to the chat: the conversation, and the
extension's form, hear the diagnosis and nothing else.

What it writes goes through `extensions.write` like anything OneAI writes:
the guard, the second reading, kept off. The mended version runs only once an
administrator turns it on.
"""

import frappe
from frappe import _, _lt

from onedesk.one import roles
from onedesk.one_studio import extensions, guard

MEND = "studio_mend"

#: An extension's Errors tab (one/tabs.py), drawn by extension_errors.js.
TABS = [{"name": "errors", "label": _lt("Errors"), "order": 85, "doctypes": ("Extension",)}]

#: How many of its latest errors it is shown, and how much of each.
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


def prompt(doc, errors: list[str]) -> str:
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
		f"Its latest errors. Each was caught: the record still saved, or the form went on working. "
		f"Line numbers count {header} added before the code:\n\n" + "\n\n---\n\n".join(errors)
	)


@frappe.whitelist(methods=["POST"])
def mend(extension: str) -> dict:
	"""Ask the mender what went wrong with an extension and have it mended,
	kept off. Answers the diagnosis, and whether the mended version passed its
	review; never the code."""
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
	if not logged:
		frappe.throw(_("{0} has run into no errors, so there is nothing to fix.").format(doc.title))
	said = read(run.once(MEND, prompt(doc, [(one or "")[-EACH:] for one in logged]))) or {}
	diagnosis = str(said.get("diagnosis") or "").strip()[:600]
	code = str(said.get("code") or "").strip()
	if not diagnosis or not code:
		frappe.throw(
			_("OneAI could not work out what went wrong with {0}. Try again later.").format(doc.title)
		)
	if code == (doc.code or "").strip():
		frappe.throw(_("OneAI could not fix {0}: {1}").format(doc.title, diagnosis))
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
		)
	except guard.Refused as refused:
		frappe.throw(_("OneAI's fixed version was not kept: {0}").format(refused))
	return {"extension": doc.name, "diagnosis": diagnosis, "review": kept["review"], "why": kept["why"]}


@frappe.whitelist()
def listed(extension: str) -> list[dict]:
	"""The Errors tab of an extension: its errors in the last two weeks."""
	roles.require()
	frappe.get_doc(extensions.EXTENSION, extension).check_permission("read")
	return errors(extension)


def start(doc) -> str:
	"""The Fix With OneAI button: mending reads and writes with two model
	calls, minutes rather than seconds, so it is a job, and the person who
	pressed it is told when it is done."""
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
	)
	return _("OneAI is fixing it. It takes a few minutes; you will be told when it is done.")


def in_background(extension: str, told: str) -> None:
	"""The job behind the button, run as whoever pressed it."""
	title = frappe.db.get_value(extensions.EXTENSION, extension, "title") or extension
	try:
		said = mend(extension)
	except frappe.ValidationError as e:
		frappe.clear_last_message()
		message, indicator = str(e), "red"
	else:
		if said["review"] == "Passed":
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
