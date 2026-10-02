"""OneAI in OneStudio: it writes the workspace's extensions, and is the only
thing that does.

- `extensions_here` reads what the workspace has: each extension, where and
  when it runs, whether it is on, its review, and whether it ran into a
  error lately. No code.
- `write_extension` keeps what OneAI wrote, off, after the guard and the
  review (extensions.write), and makes a card whose Turn On does what the
  administrator would do in the list. A refused review comes back to the
  model to mend, under the same extension. The code it wrote is left out of
  the conversation as it is kept and shown (`unshown`), so it is in the
  extension alone; changing one is writing it again from what it does.

Both run on OneStudio Extensions (`studio`), a stronger model than the
chat's, which is told what an extension may do.
"""

from typing import Annotated, Literal

import frappe
from frappe import _, _lt

from onedesk.one import roles
from onedesk.one_studio import extensions, guard, record_types

SUGGESTIONS = {
	"Record Type": [
		{
			# The reader says what is kept; the model designs the fields.
			"label": _lt("Make a record type…"),
			"ask": _lt("Make a record type for "),
			"fill": True,
			"expects": "design_record_type",
		},
		{
			"label": _lt("Add a field to this one…"),
			"ask": _lt("Add a field to this record type: "),
			"fill": True,
			"view": "Form",
			"expects": "design_record_type",
		},
	],
	"Extension": [
		{
			# The reader says what; the model writes it.
			"label": _lt("Write an extension…"),
			"ask": _lt("Write an extension that "),
			"fill": True,
			"expects": "write_extension",
		},
		{
			"label": _lt("What do our extensions do?"),
			"ask": _lt(
				"Which extensions does this workspace have, what does each do, and is any of them failing?"
			),
			"expects": "extensions_here",
			"view": "List",
		},
		{
			# Changing one is writing it again: reviewed again, off until approved.
			"label": _lt("Change this one…"),
			"ask": _lt("Change this extension so that "),
			"fill": True,
			"view": "Form",
			"expects": "write_extension",
		},
		{
			"label": _lt("Has this one run into errors?"),
			"ask": _lt("Has this extension run into errors lately, and what went wrong?"),
			"view": "Form",
			"expects": "extension_mistakes",
			"when": {"enabled": [1]},
		},
		{
			"label": _lt("Why is this one off?"),
			"ask": _lt("Why is this extension off, and what would it take to turn it on?"),
			"view": "Form",
			"when": {"enabled": [0]},
		},
	],
}


def _recent_mistakes(name: str) -> int:
	return frappe.db.count(
		"Error Log",
		{"method": f"{guard.TITLE}{name}", "creation": [">=", extensions.since(name, 7)]},
	)


def extensions_here(
	record: Annotated[str, "A kind of record, such as Customer, to read only its extensions."] | None = None,
) -> dict:
	"""The workspace's extensions, for its administrators: each one's title,
	where and when it runs, whether it is on, what it does, its review, and
	how often it ran into an error in the last week. Read it before writing
	or changing one."""
	if not roles.administers():
		return {"error": "Only a workspace administrator sees the extensions."}
	filters = {"record_doctype": record} if record else {}
	rows = frappe.get_list(
		extensions.EXTENSION,
		filters=filters,
		fields=[
			"name",
			"title",
			"runs",
			"record_doctype",
			"view",
			"event",
			"enabled",
			"explanation",
			"review",
			"review_note",
		],
		order_by="modified desc",
		limit=50,
	)
	for row in rows:
		row["mistakes_this_week"] = _recent_mistakes(row.name)
	return {
		"extensions": rows,
		"server_extensions_run_here": extensions.runs_server_scripts(),
	}


def extension_mistakes(
	extension: Annotated[str, "The extension's name, as it is in the address of its page."],
) -> dict:
	"""For a workspace administrator: the errors one extension ran into in the
	last two weeks, newest first, each with when, on which record, and what
	went wrong in one line. Never its code. Read it before saying why an
	extension is failing; mend_extension mends it."""
	from onedesk.one_studio import mend

	if not roles.administers():
		return {"error": "Only a workspace administrator sees the extensions."}
	if not frappe.db.exists(extensions.EXTENSION, extension):
		return {"error": f"There is no extension {extension}."}
	return {
		"extension": extension,
		"title": frappe.db.get_value(extensions.EXTENSION, extension, "title"),
		"errors": mend.errors(extension, limit=10),
	}


def mend_extension(
	extension: Annotated[str, "The extension's name, as it is in the address of its page."],
) -> dict:
	"""Mend an extension that has run into errors: a separate reading of its
	code and its errors says what went wrong and writes it again, reviewed and
	kept off. Answers what went wrong, never the code; the card turns the
	mended version on when the person approves it."""
	from onedesk.one_studio import mend

	if not roles.administers():
		return {"error": "Only a workspace administrator may have an extension mended."}
	try:
		mended = mend.mend(extension)
	except frappe.ValidationError as e:
		frappe.clear_last_message()
		return {"error": str(e)}
	if mended["review"] != "Passed":
		return {
			"diagnosis": mended["diagnosis"],
			"error": f"The mended version was kept off: the review refused it. {mended['why']}",
		}
	doc = frappe.get_doc(extensions.EXTENSION, extension)
	return {
		"diagnosis": mended["diagnosis"],
		**_proposed(doc, _("Fixed: {0}").format(mended["diagnosis"])),
		"next": "Say in plain words what went wrong and that approving turns the mended version on. Do not show the code.",
	}


def write_extension(
	title: Annotated[
		str, "What it is called, a name in Title Case, such as A Customer Needs a Mobile Number."
	],
	runs: Annotated[Literal["On Screen", "On Server"], "Where it runs."],
	record: Annotated[str, "The kind of record it runs on, as its DocType name, such as Customer."],
	explanation: Annotated[
		str, "What it does and when, in one or two plain sentences for somebody who does not read code."
	],
	code: Annotated[str, "The code: JavaScript for On Screen, restricted Python for On Server."],
	asked: Annotated[str, "What the person asked for, in their words."],
	view: Annotated[Literal["Form", "List"], "On Screen only: the form or the list."] | None = None,
	event: Annotated[
		str,
		"On Server only: Before Insert, Before Validate, Before Save, After Insert, After Save, Before Submit, After Submit, Before Cancel, After Cancel or Before Delete.",
	]
	| None = None,
	extension: Annotated[str, "To change an extension, or to mend one the review refused: its name."]
	| None = None,
) -> dict:
	"""Write an extension: code that runs on the screen or on the server for
	one kind of record. It is kept off, read by a second reviewer, and turned
	on only when the person approves the card."""
	if not roles.administers():
		return {"error": "Only a workspace administrator may have an extension written."}
	try:
		kept = extensions.write(
			title=title,
			runs=runs,
			doctype=record,
			explanation=explanation,
			code=code,
			asked=asked,
			view=view,
			event=event,
			extension=extension,
		)
	except guard.Refused as refused:
		return {"mend": "write_extension", "error": f"Not kept: {refused}"}
	except frappe.ValidationError as e:
		frappe.clear_last_message()
		return {"mend": "write_extension", "error": str(e)}
	if kept["review"] != "Passed":
		return {
			"mend": "write_extension",
			"error": f"Kept off: the review refused it. {kept['why']} Write it again with extension={kept['extension']}.",
		}
	doc = frappe.get_doc(extensions.EXTENSION, kept["extension"])
	return {
		**_proposed(doc, asked),
		"next": "Say in one sentence what it does, and that approving turns it on. Do not show the code.",
	}


def _proposed(doc, why: str) -> dict:
	"""The card that turns an extension on, as it stands, when approved."""
	from onedesk.one_ai import proposals

	where = _("{0}, {1}").format(
		_(doc.runs), _(doc.event) if doc.runs == extensions.ON_SERVER else _(doc.view)
	)
	changes = {
		"what": "extension",
		"extension": doc.name,
		"state": extensions.reviewed_as(doc),
		"title": doc.title,
		"summary": [
			{"label": _("Runs"), "value": where},
			{"label": _("Record"), "value": _(doc.record_doctype)},
			{"label": _("Explanation"), "value": doc.explanation},
			{"label": _("Review"), "value": doc.review_note or _(doc.review)},
		],
		"route": ["Form", extensions.EXTENSION, doc.name],
	}
	return {
		"proposal": proposals.propose("Setup", extensions.EXTENSION, changes=changes, why=why),
		"state": "Proposed",
	}


def turn_on(changes: dict) -> str:
	"""A Setup card for an extension approved: turned on, as whoever pressed
	Approve, if it is still the code that was shown."""
	doc = frappe.get_doc(extensions.EXTENSION, changes["extension"])
	if extensions.reviewed_as(doc) != changes.get("state"):
		raise frappe.ValidationError(
			_("{0} has changed since this was suggested, so it no longer applies.").format(doc.title)
		)
	doc.enabled = 1
	doc.save()
	return doc.name


def design_record_type(
	title: Annotated[str, "Its name, a singular noun in Title Case, such as Membership."],
	app: Annotated[
		str,
		"The app it belongs to, whose people use it: One, OneCRM, OneBook, OneInventory, OneProject or OneHR.",
	],
	description: Annotated[str, "What one of these records is, in one plain sentence."],
	fields: Annotated[
		list[dict],
		"Its fields, in order: each {label, fieldtype, options?, reqd?, in_list_view?, description?}. fieldtype is one of "
		+ ", ".join(record_types.FIELDTYPES)
		+ ". options is the kind of record for a Link, the choices one a line for a Select. The first Data field is its title.",
	],
	asked: Annotated[str, "What the person asked for, in their words."],
	record_type: Annotated[str, "To change a record type the workspace already has: its name."] | None = None,
) -> dict:
	"""Design a kind of record the workspace keeps of its own, such as
	memberships or vehicles, or change one it has: its fields, the app it
	belongs to, and what it is. Nothing is made until the person approves
	the card."""
	if not roles.administers():
		return {"error": "Only a workspace administrator may have a record type made."}
	try:
		record_types.check(title, app, fields, record_type=record_type)
	except record_types.Refused as refused:
		return {"mend": "design_record_type", "error": str(refused)}
	from onedesk.one_ai import proposals

	shown = [one.get("label") for one in fields if one.get("label")]
	changes = {
		"what": "record_type",
		"title": title if not record_type else record_type,
		"app": app,
		"description": description,
		"fields": fields,
		"asked": asked,
		"record_type": record_type,
		"summary": [
			{"label": _("App"), "value": _(app)},
			{"label": _("Description"), "value": description},
			{"label": _("Fields"), "value": ", ".join(shown)},
		],
		"route": ["List", title] if not record_type else ["Form", record_types.RECORD_TYPE, record_type],
	}
	return {
		"proposal": proposals.propose("Setup", record_types.RECORD_TYPE, changes=changes, why=asked),
		"state": "Proposed",
		"next": "Say in one sentence what it is and where it will be. Nothing is made until they approve it.",
	}


def record_types_here() -> dict:
	"""The record types the workspace keeps of its own: each one's app, what
	it is, its fields and how many records it has. Read it before designing
	or changing one."""
	if not roles.administers():
		return {"error": "Only a workspace administrator sees the record types."}
	out = []
	for row in frappe.get_list(
		record_types.RECORD_TYPE, fields=["name", "record_doctype", "app", "description"], limit=100
	):
		meta = frappe.get_meta(row.record_doctype)
		row["fields"] = [
			f"{df.label} ({df.fieldtype}{', ' + df.options if df.options else ''})"
			for df in meta.fields
			if df.label and not df.hidden
		]
		row["records"] = frappe.db.count(row.record_doctype)
		out.append(row)
	return {"record_types": out, "apps": list(record_types._apps())}


def make_record_type(changes: dict) -> str:
	"""A Setup card for a record type approved, as whoever pressed Approve."""
	if changes.get("record_type"):
		return record_types.change(
			changes["record_type"],
			changes["app"],
			changes["description"],
			changes["fields"],
			changes["asked"],
		)
	return record_types.make(
		changes["title"], changes["app"], changes["description"], changes["fields"], changes["asked"]
	)


write_extension.action = mend_extension.action = design_record_type.action = "studio"
write_extension.unshown = ("code",)
