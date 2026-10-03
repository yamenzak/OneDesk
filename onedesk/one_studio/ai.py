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
  extension alone.
- `extension_code` hands OneAI the code it is changing, so a change edits it
  rather than rewriting it from the explanation. Its answer's code is
  `unshown` too: the run reads it, the kept conversation does not.

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
	record: Annotated[
		str,
		"Only to narrow to one kind of record the extensions run on, such as Customer. Leave it out to read them all.",
	]
	| None = None,
) -> dict:
	"""The workspace's extensions, for its administrators: each one's title,
	where and when it runs, whether it is on, what it does, its review, and
	how often it ran into an error in the last week. Read it before writing
	or changing one."""
	if not roles.administers():
		return {"error": "Only a workspace administrator sees the extensions."}
	# A model on the Extensions list reads "Extension" as the kind to narrow
	# to, and was told there were none (measured, Gemma 4).
	if record == extensions.EXTENSION:
		record = None
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
			"place",
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


def _named(extension: str | None) -> str | None:
	"""An extension's name, given its name or its title: a model asked about
	"Create Call Task" passes the title it read (measured, Gemma 4)."""
	if not extension or frappe.db.exists(extensions.EXTENSION, extension):
		return extension
	return frappe.db.get_value(extensions.EXTENSION, {"title": extension}, "name") or extension


def extension_mistakes(
	extension: Annotated[str, "The extension's name, as it is in the address of its page, or its title."],
) -> dict:
	"""For a workspace administrator: the errors one extension ran into in the
	last two weeks, newest first, each with when, on which record, and what
	went wrong in one line. Never its code. Read it before saying why an
	extension is failing; mend_extension mends it."""
	from onedesk.one_studio import mend

	if not roles.administers():
		return {"error": "Only a workspace administrator sees the extensions."}
	extension = _named(extension)
	if not frappe.db.exists(extensions.EXTENSION, extension):
		return {"error": f"There is no extension {extension}."}
	return {
		"extension": extension,
		"title": frappe.db.get_value(extensions.EXTENSION, extension, "title"),
		"errors": mend.errors(extension, limit=10),
	}


def extension_code(
	extension: Annotated[str, "The extension's name, as it is in the address of its page, or its title."],
) -> dict:
	"""Before changing an extension: what it is now, its code included, to
	change rather than write again from its explanation. For OneAI alone: the
	code is left out of the conversation as it is kept and shown, and is never
	said to the person."""
	if not roles.administers():
		return {"error": "Only a workspace administrator may have an extension changed."}
	extension = _named(extension)
	if not frappe.db.exists(extensions.EXTENSION, extension):
		return {"error": f"There is no extension {extension}."}
	doc = frappe.get_doc(extensions.EXTENSION, extension)
	return {
		"extension": doc.name,
		"title": doc.title,
		"runs": doc.runs,
		"record": doc.record_doctype,
		"view": doc.view if doc.runs == extensions.ON_SCREEN else None,
		"event": doc.event if doc.runs == extensions.ON_SERVER else None,
		"explanation": doc.explanation,
		"code": doc.code,
		"next": "Change what was asked and keep the rest as it is, then call write_extension with the whole code and extension set to its name. Never show the code.",
	}


def mend_extension(
	extension: Annotated[str, "The extension's name, as it is in the address of its page, or its title."],
	problem: Annotated[
		str,
		"What the person says it does wrong, in their words. Needed when it has run into no errors, such as one that never does its work.",
	]
	| None = None,
) -> dict:
	"""Fix an extension that has run into errors, or that the person says
	does not do what it should: a separate reading of its code, its errors and
	what they say works out what went wrong and writes it again, reviewed and
	kept off. It takes about a minute, so it runs on its own and the person is
	told when it is done; they turn the fixed version on from its page."""
	from onedesk.one_studio import mend

	if not roles.administers():
		return {"error": "Only a workspace administrator may have an extension fixed."}
	extension = _named(extension)
	if not frappe.db.exists(extensions.EXTENSION, extension):
		return {"error": f"There is no extension {extension}."}
	doc = frappe.get_doc(extensions.EXTENSION, extension)
	if not problem and not _recent_mistakes(doc.name):
		return {
			"error": f"{doc.title} has run into no errors. Ask the person what it does wrong and call again with problem."
		}
	return {
		"extension": doc.name,
		"title": doc.title,
		"started": mend.start(doc, problem),
		"next": "Say that OneAI is fixing it, that it takes about a minute and they will be told what went wrong, and that the fixed version stays off until they turn it on from its page.",
	}


def _unescaped(code: str | None) -> str | None:
	"""Code with its line breaks written out as `\\n`, read as the lines it
	meant. Measured: Gemma 4 sent a whole extension on one line that way, and
	the review refused it as not Python. Only code with no line break of its
	own, so code that means a `\\n` inside a string keeps it."""
	if code and "\n" not in code and "\\n" in code:
		return code.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\t", "\t").replace('\\"', '"')
	return code


def extension_places() -> dict:
	"""One's own pages an extension can run on, beyond frappe's forms and
	lists: OneMail, OneCalendar, OneTask, OneCloud, OneIntake, the pipeline
	board, every space's home and a record's head. For each: when it runs,
	what the extension is told, and the few things it may do there. Read it
	before writing an extension for one of them."""
	from onedesk.one_studio import places

	if not roles.administers():
		return {"error": "Only a workspace administrator has extensions written."}
	return {
		"places": places.described(),
		"how": 'one.on("<event>", (data, page) => { ... }): data is what the place gives, page has only what it may do. '
		"Write every word a person reads in __().",
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
	view: Annotated[
		Literal["Form", "List", "Page"],
		"On Screen only: the form, the list, or one of One's pages (give place).",
	]
	| None = None,
	event: Annotated[
		str,
		"On Server only. On a record's event: Before Insert, Before Validate, Before Save, After Insert, After Save, "
		"Before Submit, After Submit, Before Cancel, After Cancel, Before Save (Submitted Document), "
		"After Save (Submitted Document), Before Delete or After Delete. On its own, with no doc: Every Hour, "
		"Every Day, Every Week, Every Month, or On a Schedule (give cron).",
	]
	| None = None,
	extension: Annotated[
		str, "To change an extension, or to mend one the review refused: its name, or its title."
	]
	| None = None,
	place: Annotated[
		str,
		"On one of One's pages only: where and when, as extension_places names it, such as onemail.conversation.",
	]
	| None = None,
	cron: Annotated[
		str,
		"On a Schedule only: when, as a cron line, at most hourly, such as 0 8 * * 1-5 for 8:00 each weekday.",
	]
	| None = None,
) -> dict:
	"""Write an extension: code that runs on the screen or on the server for
	one kind of record. It is kept off, read by a second reviewer, and turned
	on only when the person approves the card."""
	if not roles.administers():
		return {"error": "Only a workspace administrator may have an extension written."}
	extension = _named(extension)
	if extension and not frappe.db.exists(extensions.EXTENSION, extension):
		# Measured on Gemma 4: refused by the guard, so never kept, then
		# mended "with extension=" its own title. There is nothing to change:
		# it is a new one.
		extension = None
	if extension:
		# A change that leaves out where or when keeps what it has: measured,
		# Gemma changing a limit sent the code and no event, and was refused.
		was = frappe.db.get_value(
			extensions.EXTENSION, extension, ["view", "event", "place", "cron"], as_dict=True
		)
		view, event, place = view or was.view, event or was.event, place or was.place
		cron = cron or was.cron
	try:
		kept = extensions.write(
			title=title,
			runs=runs,
			doctype=record,
			explanation=explanation,
			code=_unescaped(code),
			asked=asked,
			view=view,
			event=event,
			extension=extension,
			place=place,
			cron=cron,
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
			"tried": kept["tried"],
		}
	doc = frappe.get_doc(extensions.EXTENSION, kept["extension"])
	return {
		**_proposed(doc, asked),
		"tried": kept["tried"],
		"next": "If what it did when tried is not what was asked, write it again with "
		f"extension={doc.name}. Otherwise say in one sentence what it does, and that approving turns it on. "
		"Do not show the code.",
	}


def _proposed(doc, why: str) -> dict:
	"""The card that turns an extension on, as it stands, when approved."""
	from onedesk.one_ai import proposals

	where = (
		extensions._place_said(doc)
		if doc.view == extensions.PAGE
		else _("{0}, {1}").format(
			_(doc.runs),
			(f"{_(doc.event)} ({doc.cron})" if doc.get("cron") else _(doc.event))
			if doc.runs == extensions.ON_SERVER
			else _(doc.view),
		)
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


def forms_here(
	record: Annotated[
		str,
		"Only to read what was changed on one form, such as Customer. Leave it out for every changed form.",
	]
	| None = None,
) -> dict:
	"""The forms the workspace has changed (OneStudio, Forms): each with how
	many of its customizations are the workspace's and how many extensions run
	on it, or, for one form, each change itself: a field added, hidden,
	renamed, required or in the list, the head's own rows, and its
	extensions. Read it before suggesting a change to a form."""
	if not roles.administers():
		return {"error": "Only a workspace administrator sees how forms were changed."}
	from onedesk.one_studio import forms

	if not record:
		changed = [one for one in forms.forms() if one["changes"] or one["extensions"]]
		return {"changed_forms": changed, "forms_that_may_be_changed": len(forms.forms())}
	if not frappe.db.exists("DocType", record):
		return {"error": f"{record} is not a form here."}
	from onedesk.one import customize as page

	ledger = frappe.get_all(
		"Workspace Customization", filters={"record_doctype": record}, fields=["kind", "row"]
	)
	added = [one.row for one in ledger if one.kind == "Custom Field"]
	changes = [
		{"field": row.field_name, "property": row.property, "value": row.value}
		for row in frappe.get_all(
			"Property Setter",
			filters={"name": ["in", [one.row for one in ledger if one.kind == "Property Setter"] or [""]]},
			fields=["field_name", "property", "value"],
		)
	]
	return {
		"form": record,
		"fields_added": [
			{"field": row.fieldname, "label": row.label, "type": row.fieldtype}
			for row in frappe.get_all(
				"Custom Field",
				filters={"name": ["in", added or [""]]},
				fields=["fieldname", "label", "fieldtype"],
			)
		],
		"fields_changed": changes,
		"extensions": forms.extensions(record),
		# What the buttons, charts and numbers above the fields may name.
		"choices": {
			key: value
			for key, value in page.load(record)["choices"].items()
			if key in ("verbs", "charts", "measures")
		},
	}


def form_relations(
	record: Annotated[str, "The form a field is being added to, as its DocType name, such as Item."],
) -> dict:
	"""Which other forms a field added to this one might belong on too: the
	tables of other forms that link to it (Item's Sales Invoice Item, Purchase
	Order Item and the rest, each filled from it through that link), the forms
	that link to it, and the fields it has now, so a field is not added twice.
	Read it before suggesting a new field."""
	if not roles.administers():
		return {"error": "Only a workspace administrator customizes a form."}
	from onedesk.one import customize as page

	try:
		page.may(record)
	except (frappe.ValidationError, frappe.PermissionError) as refused:
		return {"error": frappe.utils.strip_html(str(refused))}
	links = frappe.get_all(
		"DocField",
		filters={"fieldtype": "Link", "options": record, "parenttype": "DocType"},
		fields=["parent", "fieldname", "label"],
	) + frappe.get_all(
		"Custom Field",
		filters={"fieldtype": "Link", "options": record},
		fields=["dt as parent", "fieldname", "label"],
	)
	tables, forms, seen = [], [], set()
	for one in links:
		if one.parent == record or one.parent in seen:
			continue
		seen.add(one.parent)
		meta = frappe.get_meta(one.parent)
		try:
			page.may_carry(one.parent, record)
		except (frappe.ValidationError, frappe.PermissionError):
			continue
		if meta.istable:
			parents = sorted(
				set(
					frappe.get_all(
						"DocField",
						filters={"fieldtype": ["in", ["Table", "Table MultiSelect"]], "options": one.parent},
						pluck="parent",
					)
				)
			)
			tables.append(
				{"table": one.parent, "through": page.links_to(one.parent, record), "in": parents[:12]}
			)
		else:
			forms.append({"form": one.parent, "through": page.links_to(one.parent, record)})
	fields = [
		f"{df.label} ({df.fieldtype})"
		for df in frappe.get_meta(record).fields
		if df.label and df.fieldtype not in ("Section Break", "Column Break", "Tab Break")
	]
	return {
		"form": record,
		"fields_now": fields,
		"tables_linking_here": sorted(tables, key=lambda one: one["table"])[:40],
		"forms_linking_here": sorted(forms, key=lambda one: one["form"])[:40],
		"next": "Recommend which of these should carry the new field, and why, in a sentence each: a table "
		"whose rows show this form's details (an invoice's items, an order's items) usually should, filled "
		"from here; a form that only points here usually should not. Ask before adding them.",
	}


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


write_extension.action = mend_extension.action = design_record_type.action = extension_code.action = "studio"
extension_places.action = "studio"
form_relations.action = "studio"
write_extension.unshown = extension_code.unshown = ("code",)
