"""OneAI on a form's own page (one/agent.py lists this tool): the changes an
administrator asks of a kind of record's form, written as one card that
OneStudio's customize applies."""

from typing import Annotated

import frappe
from frappe import _

FIELD_SAYS = {
	"required": "reqd",
	"unique": "unique",
	"default": "default",
	"description": "description",
	"placeholder": "placeholder",
	"in_list": "in_list_view",
	"in_filter": "in_standard_filter",
	"bold": "bold",
	"read_only": "read_only",
	"show_when": "depends_on",
	"required_when": "mandatory_depends_on",
	"read_only_when": "read_only_depends_on",
	"fetch_from": "fetch_from",
	"length": "length",
	"non_negative": "non_negative",
	"precision": "precision",
	"no_copy": "no_copy",
	"allow_on_submit": "allow_on_submit",
	"print_hide": "print_hide",
	"set_only_once": "set_only_once",
	"in_quick_entry": "allow_in_quick_entry",
}


def customize(
	doctype: Annotated[str, "The form, by its record type's name, such as Item or Sales Invoice."],
	add: Annotated[
		list[dict],
		"New fields, each {label, kind, choices, after, also_on, and any of: required, unique, default, "
		"description, placeholder, in_list, in_filter, bold, read_only, show_when, required_when, "
		"read_only_when, fetch_from, length, non_negative, precision, no_copy, allow_on_submit, print_hide, "
		"set_only_once, in_quick_entry}. kind is Data, Small Text, Text, Text Editor, Int, Float, Currency, "
		"Percent, Check, Date, Datetime, Time, Duration, Select, Link, Phone, Rating, Attach, Attach Image, "
		"Color or a Section Break, Column Break or Tab Break. choices are a Select's options, a Link's form, "
		"or for Data one of Email, Name, Phone, URL, Barcode, IBAN, which are then checked. show_when and "
		"the other conditions are a field's name or eval:doc.field == 'value'. fetch_from is "
		"link_field.field_there. also_on carries the same field to other forms, each {form, fetch, through, "
		"editable}: fetch fills it from this form through their Link field (an Item field onto Sales "
		"Invoice Item through item_code); fetch false copies it when one is made from the other (a Sales "
		"Order field onto Delivery Note).",
	]
	| None = None,
	change: Annotated[
		list[dict],
		"Fields the form has, each {field, label, hidden, required, in_list, after}, and for a field added "
		"here any property add takes: field is its name or label, and only what is given changes.",
	]
	| None = None,
	remove: Annotated[list[str], "Fields added here to take away, by name or label."] | None = None,
	carry: Annotated[
		list[dict],
		"A field the form has already, carried to other forms as also_on does, each {field, form, fetch, "
		"through, editable}: field is its name or label (Item's Country of Origin onto Sales Invoice Item).",
	]
	| None = None,
	band: Annotated[
		list[dict],
		"Numbers under the title, each {label, source, field, link_field, of_doctype, filters, measure, "
		"tone}. source is Field, Linked Field, Count, Sum or Measure.",
	]
	| None = None,
	buttons: Annotated[
		list[dict], "Buttons that do something, each {verb, label, primary}: verb is one forms_here lists."
	]
	| None = None,
	charts: Annotated[
		list[dict], "Charts beside the numbers, each {chart, label}: chart is one forms_here lists."
	]
	| None = None,
	linked: Annotated[
		list[dict],
		"Sections of a linked record's fields, edited on this form, each {label, through, fields, in_tab_of}: "
		"through is a Link field of this form, fields are the linked form's field names.",
	]
	| None = None,
	connections: Annotated[
		list[dict],
		"Another form's records that link here, listed under Connections, each {form, link_field, group}.",
	]
	| None = None,
	go_to: Annotated[
		list[dict],
		"Buttons that open a place in the desk, each {label, route, group}: route such as /desk/item.",
	]
	| None = None,
	why: Annotated[str, "In a sentence, what the change is for."] | None = None,
) -> dict:
	"""Suggest a change to a form, as one card the workspace administrator
	approves: fields added with everything about them (checks, defaults, when
	shown, filled from a linked record) and carried to the forms that should
	have them too, fields renamed, hidden, required, moved or taken away,
	numbers, buttons and charts above the fields, and connections. Nothing that
	runs: a check no property can say is an extension (write_extension).
	Workspace administrators only. Read forms_here and form_relations first."""
	from frappe.utils import strip_html

	from onedesk.one import roles as workspace
	from onedesk.one_ai import proposals
	from onedesk.one_studio import customize as page

	if not workspace.administers():
		return {"error": "Only a workspace administrator customizes a form."}
	try:
		page.may(doctype)
		said = page.load(doctype)
		values, summary = said["values"], []
		fields = values["fields"]
		values["carry"] = []

		def find(name):
			key = frappe.scrub(str(name or ""))
			for row in fields:
				if name == row["fieldname"] or (key and key == frappe.scrub(row["label"] or "")):
					return row
			return None

		def missing(name) -> dict:
			shown = [f"{row['fieldname']} ({row['label']})" for row in fields if row["label"]]
			return {"error": f"{doctype} has no field {name}. Its fields: {', '.join(shown[:80])}."}

		def place(row, after) -> None:
			there = find(after)
			if row in fields:
				fields.remove(row)
			fields.insert(fields.index(there) + 1 if there else len(fields), row)

		def properties(one: dict, row: dict) -> list[str]:
			"""The model's words for a field's properties, onto the row; what was set."""
			said_of = []
			for key, prop in FIELD_SAYS.items():
				if one.get(key) in (None, ""):
					continue
				value = one[key]
				row[prop] = (1 if value else 0) if isinstance(value, bool) else value
				said_of.append(
					key.replace("_", " ")
					if isinstance(value, bool) and value
					else f"{key.replace('_', ' ')} {value}"
				)
			return said_of

		for one in change or []:
			row = find(one.get("field"))
			if not row:
				return missing(one.get("field"))
			label = row["label"] or row["fieldname"]
			said_of, called = [], _(label)
			if one.get("label"):
				row["label"] = one["label"]
				said_of.append(_("called {0}").format(one["label"]))
			if row.get("mine"):
				said_of += properties({k: v for k, v in one.items() if k in FIELD_SAYS}, row)
			else:
				for key, prop, yes, no in (
					("hidden", "hidden", _("hidden"), _("shown")),
					("required", "reqd", _("required"), _("optional")),
					("in_list", "in_list_view", _("in the list"), _("not in the list")),
				):
					if one.get(key) is not None:
						row[prop] = 1 if one[key] else 0
						said_of.append(yes if one[key] else no)
			if one.get("after"):
				if not find(one["after"]):
					return missing(one["after"])
				place(row, one["after"])
				before = find(one["after"])["label"] or one["after"]
				said_of.append(_("after {0}").format(_(before)))
			summary.append({"label": called, "value": ", ".join(said_of)})

		for name in remove or []:
			row = find(name)
			if not row:
				return missing(name)
			if not row.get("mine"):
				return {
					"error": f"{row['label'] or name} came with {doctype}; it can be hidden, not taken away."
				}
			fields.remove(row)
			summary.append({"label": _("Removed"), "value": row["label"] or name})

		for one in add or []:
			kind = one.get("kind") or "Data"
			choices = one.get("choices")
			row = {
				"fieldname": None,
				"label": one.get("label") or "",
				"fieldtype": kind,
				"options": "\n".join(choices) if isinstance(choices, list) else (choices or ""),
				"hidden": 0,
				"reqd": 0,
				"in_list_view": 0,
				"mine": 1,
			}
			said_of = properties(one, row)
			if one.get("after") and not find(one["after"]):
				return missing(one["after"])
			place(row, one.get("after"))
			summary.append(
				{
					"label": _("New field"),
					"value": f"{row['label']} ({_(kind)})" + (f": {', '.join(said_of)}" if said_of else ""),
				}
			)
			for other in one.get("also_on") or []:
				form = other.get("form") if isinstance(other, dict) else other
				fetch = other.get("fetch", True) if isinstance(other, dict) else True
				values["carry"].append(
					{
						"to": form,
						"label": row["label"],
						"fetch": 1 if fetch else 0,
						"through": other.get("through") if isinstance(other, dict) else None,
						"editable": 1 if isinstance(other, dict) and other.get("editable") else 0,
					}
				)
				summary.append(
					{
						"label": _("Also on {0}").format(_(form)),
						"value": _("{0}, filled from {1}").format(row["label"], _(doctype))
						if fetch
						else _("{0}, copied when made from {1}").format(row["label"], _(doctype)),
					}
				)

		for one in carry or []:
			row = find(one.get("field"))
			if not row:
				return missing(one.get("field"))
			fetch = one.get("fetch", True)
			values["carry"].append(
				{
					"to": one.get("form"),
					"label": row["label"],
					"fetch": 1 if fetch else 0,
					"through": one.get("through"),
					"editable": 1 if one.get("editable") else 0,
				}
			)
			summary.append(
				{
					"label": _("Also on {0}").format(_(one.get("form") or "")),
					"value": _("{0}, filled from {1}").format(_(row["label"]), _(doctype))
					if fetch
					else _("{0}, copied when made from {1}").format(_(row["label"]), _(doctype)),
				}
			)

		for one in band or []:
			values["band"].append({key: one.get(key) for key in page.HEAD_COLUMNS["band"] if one.get(key)})
			summary.append({"label": _("Under the title"), "value": one.get("label") or ""})

		for one in buttons or []:
			values["verbs"].append(
				{
					"verb": one.get("verb"),
					"label": one.get("label"),
					"primary": 1 if one.get("primary") else 0,
				}
			)
			summary.append({"label": _("Button"), "value": one.get("label") or one.get("verb") or ""})

		for one in charts or []:
			values["charts"].append({"chart": one.get("chart"), "label": one.get("label")})
			summary.append({"label": _("Chart"), "value": one.get("label") or one.get("chart") or ""})

		for one in linked or []:
			through = find(one.get("through"))
			if not through:
				return missing(one.get("through"))
			names = one.get("fields") or []
			values["linked"].append(
				{
					"label": one.get("label"),
					"link_field": through["fieldname"],
					"fields": "\n".join(names) if isinstance(names, list) else names,
					"placed_in": (find(one.get("in_tab_of")) or {}).get("fieldname"),
				}
			)
			summary.append({"label": _("Linked section"), "value": one.get("label") or ""})

		for one in connections or []:
			values["links"].append(
				{
					"link_doctype": one.get("form"),
					"link_fieldname": one.get("link_field"),
					"group": one.get("group"),
				}
			)
			summary.append({"label": _("Connection"), "value": _(one.get("form") or "")})

		for one in go_to or []:
			values["actions"].append(
				{"label": one.get("label"), "action": one.get("route"), "group": one.get("group")}
			)
			summary.append(
				{"label": _("Goes to"), "value": f"{one.get('label') or ''} ({one.get('route') or ''})"}
			)

		if not summary:
			return {
				"error": "Say what to change: add, change, remove, carry, band, buttons, charts, linked, connections or go_to."
			}
		page._check(doctype, values)
		page._carries(doctype, values["carry"])
		for row in fields:
			if row.get("mine") and not row.get("fieldname"):
				_trial_field(doctype, row)
	except (frappe.ValidationError, frappe.PermissionError) as refused:
		return {"error": strip_html(str(refused))}
	return {
		"proposal": proposals.propose(
			"Customize",
			doctype,
			changes={"values": values, "token": said["token"], "summary": summary},
			why=why,
		),
		"state": "Proposed",
		"next": "Say in a sentence what the card changes. It changes the form for everybody once they approve "
		"it, and Reset in OneStudio › Custom Fields takes it back. If a check was asked for that no property says, "
		"offer an extension for it.",
	}


def _trial_field(doctype: str, row: dict) -> None:
	"""A new field's properties read as the save will read them, before the card
	is made: frappe's own checks and the workspace layer's, nothing written."""
	from onedesk.one import layer

	field = frappe.get_doc(
		{
			"doctype": "Custom Field",
			"dt": doctype,
			"label": row.get("label"),
			"fieldtype": row.get("fieldtype"),
			"options": row.get("options"),
			**{key: row[key] for key in layer.ADDED if row.get(key) not in (None, "")},
		}
	)
	where = row.get("label") or "?"
	layer._conditions(field, where)
	layer._fetched(field, where)
	if field.fieldtype == "Data" and (field.options or "") not in layer.DATA_OPTIONS:
		frappe.throw(
			_(
				"{0}: a text field may hold any text, or an email, a name, a phone number, a web address, a barcode or an IBAN."
			).format(where)
		)
	if field.fieldtype == "Link" and not frappe.db.exists("DocType", field.options or ""):
		frappe.throw(_("{0}: {1} is not a form here.").format(where, field.options or "?"))


customize.action = "studio"
