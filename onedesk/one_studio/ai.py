"""OneAI in OneStudio: it writes the workspace's extensions, and is the only
thing that does.

- `extensions_here` reads what the workspace has: each extension, where and
  when it runs, whether it is on, its review, and whether it ran into a
  mistake lately. No code.
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
from onedesk.one_studio import extensions, guard, review

SUGGESTIONS = {
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
			"label": _lt("Why is this one off?"),
			"ask": _lt("Why is this extension off, and what would it take to turn it on?"),
			"view": "Form",
			"when": {"enabled": [0]},
		},
	],
}


def _recent_mistakes(name: str) -> int:
	from frappe.utils import add_days, now_datetime

	return frappe.db.count(
		"Error Log",
		{"method": f"{guard.TITLE}{name}", "creation": [">=", add_days(now_datetime(), -7)]},
	)


def extensions_here(
	record: Annotated[str, "A kind of record, such as Customer, to read only its extensions."] | None = None,
) -> dict:
	"""The workspace's extensions, for its administrators: each one's title,
	where and when it runs, whether it is on, what it does, its review, and
	how often it ran into a mistake in the last week. Read it before writing
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
	from onedesk.one_ai import proposals

	doc = frappe.get_doc(extensions.EXTENSION, kept["extension"])
	where = _("{0}, {1}").format(
		_(doc.runs), _(doc.event) if doc.runs == extensions.ON_SERVER else _(doc.view)
	)
	changes = {
		"what": "extension",
		"extension": doc.name,
		"state": review.fingerprint(frappe.db.get_value(extensions.EXTENSION, doc.name, "code")),
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
		"proposal": proposals.propose("Setup", extensions.EXTENSION, changes=changes, why=asked),
		"state": "Proposed",
		"next": "Say in one sentence what it does, and that approving turns it on. Do not show the code.",
	}


def turn_on(changes: dict) -> str:
	"""A Setup card for an extension approved: turned on, as whoever pressed
	Approve, if it is still the code that was shown."""
	doc = frappe.get_doc(extensions.EXTENSION, changes["extension"])
	if review.fingerprint(frappe.db.get_value(extensions.EXTENSION, doc.name, "code")) != changes.get(
		"state"
	):
		raise frappe.ValidationError(
			_("{0} has changed since this was suggested, so it no longer applies.").format(doc.title)
		)
	doc.enabled = 1
	doc.save()
	return doc.name


write_extension.action = "studio"
write_extension.unshown = ("code",)
