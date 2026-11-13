"""OneAI on numbering (one/agent.py lists these tools): how each kind of
record is named, and a change to a series or a naming rule as a card."""

from typing import Annotated

import frappe
from frappe import _

SERIES_HELP = (
	"A series is parts joined by dots, read left to right. Text is kept as written (INV-, SO/, -). "
	"YYYY is the year (2026), YY the year's last two digits (26), MM the month (01-12), DD the day, "
	"JJJ the day of the year (001-366), WW the week of the year; FY is the fiscal year (2025-2026) and "
	"TFY its short form, ABBR the company's abbreviation; {fieldname} or a bare fieldname is that field "
	"of the record (such as {branch}), and timestamp the moment it is made. The number is # once per "
	"digit (##### gives 00001), must follow a dot, and only the first run of # counts. The number "
	"restarts whenever the text before it changes, so INV-.YYYY.-.#### starts at 0001 each year and "
	"INV-.YYYY.-.MM.-.#### each month. Only letters, digits, spaces, - / _ . # { } are allowed. "
	"Examples: INV-.YYYY.-.#####, SO/.YY./.####, .ABBR.-QTN-.#####, EMP-.{department}.-.###."
)


NAMING_HELP = (
	"A new record is named one of these ways, as the system offers them. Naming Series: the next name in one "
	"of its series (only a kind with a Naming Series field). field:<fieldname>: the value of that field, "
	"which becomes required and unique, so only a field no two records will share, such as a title or a "
	"code; the fields offered are named_by.fields. An expression: a pattern written as a series is, such "
	"as PRJ-.YYYY.-.#### for a kind with no series field, its prefix no other kind's. prompt: typed by "
	"whoever makes the record. hash: a random name. A Customer, Supplier, Item, Employee or Campaign names "
	"itself, so its choices are its app's own (named_by.kinds). A kind One's own code makes (named_by.made) "
	"is never typed by hand and only named by a field that code always fills. Naming Rules come first: a record whose "
	"fields match a rule is named by the rule's prefix and its own counter, whatever else is chosen; the "
	"highest priority matching rule wins. Nothing renames a record already made: every change applies to "
	"records made afterwards, and old ones keep their names."
)


def workspace_numbering(
	doctype: Annotated[str, "The record type, by its name, such as Sales Invoice. Empty lists them all."]
	| None = None,
) -> dict:
	"""How a kind of record is named, for the workspace's administrators:
	what a new one is named by and what else it may be (`named_by`), each
	series it may take its name from (the first is the default) with the name
	the next one gets, the number its counter has reached and the highest
	number records already use (`used`), which a counter may never go below,
	and its naming rules with what each must match. Empty: every kind of
	record numbered by a series. Read it before suggesting a change."""
	from onedesk.one import roles
	from onedesk.one_studio import numbering

	if not roles.administers():
		return {"error": "Only a workspace administrator sees how records are numbered."}
	try:
		if not doctype:
			return {"kinds": numbering.doctypes()}
		return {
			"doctype": doctype,
			"named_by": numbering.naming_by(doctype),
			"series": numbering.series(doctype),
			"rules": numbering.naming_rules(doctype),
			"how_a_record_is_named": NAMING_HELP,
			"how_a_series_is_written": SERIES_HELP,
		}
	except frappe.ValidationError as e:
		frappe.clear_last_message()
		return {"error": str(e)}


def _rule_said(doc) -> str:
	"""A naming rule, in a line: its prefix and what it matches."""
	matches = ", ".join(f"{one.field} {one.condition} {one.value}" for one in doc.conditions or [])
	said = _("{0} with {1} digits").format(doc.prefix, doc.prefix_digits)
	return _("{0}, when {1}").format(said, matches) if matches else _("{0}, for every record").format(said)


def change_numbering(
	doctype: Annotated[str, "The record type, by its name, such as Sales Invoice."],
	series: Annotated[
		list[str],
		"Every series it may be named by, the default first, when they change: the whole list, not only a new "
		"one. Only a kind with a Naming Series field. " + SERIES_HELP,
	]
	| None = None,
	move: Annotated[
		list[dict],
		"Counters to move on, each {series, to}: the next name continues after `to`. Never below what the "
		"counter has reached or the highest number records already use.",
	]
	| None = None,
	name_by: Annotated[
		str,
		"What a new one is named by: Naming Series, field:<fieldname> from named_by.fields, an expression such "
		"as PRJ-.YYYY.-.####, prompt, hash, or one of named_by.kinds for a kind that names itself. "
		+ NAMING_HELP,
	]
	| None = None,
	rules: Annotated[
		list[dict],
		"Naming rules to add, change or remove, each {name?, prefix, digits, priority, disabled, conditions, "
		"delete}: name only for an existing rule (from workspace_numbering), delete true to remove it; prefix "
		"the text before the number written as a series is but with no #, such as RET-.YYYY.-; digits 1-10; "
		"conditions [{field, condition, value}] all of which must match, condition one of = != > < >= <=, "
		"field an ordinary field of the record, none meaning every record; the higher priority wins.",
	]
	| None = None,
	why: Annotated[str, "In a sentence, what the change is for."] | None = None,
) -> dict:
	"""Suggest how a kind of record is named, as a card a workspace administrator approves: named by a
	series, one of its fields, an expression, typed or random; its series added, changed, reordered (the
	first is the default) or removed; a series' counter moved on, to start a new year at 1000 or to carry on
	after records brought in from elsewhere; and its naming rules added, changed or removed. Read
	workspace_numbering first, and check `used` before moving a counter. Nothing changes until they approve
	it, and records already made keep their names. Workspace administrators only."""
	from onedesk.one import roles
	from onedesk.one_ai import proposals
	from onedesk.one_studio import numbering

	if not roles.administers():
		return {"error": "Only a workspace administrator changes how records are numbered."}
	try:
		numbering._meta(doctype)
		now = numbering.series(doctype)
		was = [row["series"] for row in now]
		wanted = [one.strip() for one in series or [] if one and one.strip()] or was
		if series and not frappe.get_meta(doctype).get_field("naming_series"):
			return {"error": f"{doctype} has no series; name it by an expression instead."}
		if series and not wanted:
			return {"error": f"{doctype} needs at least one series."}
		if wanted != was:
			numbering.check(doctype, wanted)
		moves, summary, changed_rules = [], [], []
		if wanted != was:
			summary.append(
				{"label": _("Series"), "value": _("{0} (was {1})").format(", ".join(wanted), ", ".join(was))}
			)
		named = numbering.naming_by(doctype)
		name_by = (name_by or "").strip() or None
		if name_by and not named:
			return {"error": f"{doctype} is named by its own code, so only its rules can change."}
		if name_by and name_by != named["value"]:
			if name_by not in numbering.choices(named):
				if named["app"] or name_by.startswith("field:"):
					return {
						"error": f"{doctype} cannot be named by {name_by}; the choices are {', '.join(numbering.choices(named))}."
					}
				numbering.check_pattern(doctype, name_by)
			summary.append(
				{
					"label": _("Named By"),
					"value": _("{0} (was {1})").format(
						numbering.label(named, name_by), numbering.label(named, named["value"])
					),
				}
			)
		else:
			name_by = None
		rows = {row["series"]: row for row in now}
		for one in move or []:
			name, to = (one.get("series") or "").strip(), frappe.utils.cint(one.get("to"))
			if name not in wanted:
				return {"error": f"{name} is not one of {doctype}'s series: {', '.join(wanted)}."}
			row = rows.get(name) or {"current": 0, "used": 0}
			floor = max(row["current"], row["used"])
			if to < floor:
				return {
					"error": f"{name} has reached {floor}; a lower number would repeat a name already used."
				}
			if to == row["current"]:
				continue
			moves.append({"series": name, "to": to})
			summary.append(
				{"label": name, "value": _("Continues after {0} (was {1})").format(to, row["current"])}
			)
		for one in rules or []:
			if one.get("delete"):
				if not one.get("name") or not frappe.db.exists(
					"Document Naming Rule", {"name": one["name"], "document_type": doctype}
				):
					return {"error": f"{one.get('name')} is not a rule of {doctype}."}
				changed_rules.append({"name": one["name"], "delete": True})
				summary.append({"label": _("Rule"), "value": _("Remove {0}").format(one["name"])})
				continue
			doc = numbering.rule_doc(doctype, one)
			changed_rules.append(
				{
					key: one.get(key)
					for key in ("name", "prefix", "digits", "priority", "disabled", "conditions")
				}
			)
			summary.append(
				{"label": _("Rule") if one.get("name") else _("New Rule"), "value": _rule_said(doc)}
			)
	except frappe.ValidationError as e:
		frappe.clear_last_message()
		return {"error": str(e)}
	if not summary:
		return {
			"error": "That is how it is numbered already, so there is nothing to change. Say it is right as it is."
		}
	return {
		"proposal": proposals.propose(
			"Numbering",
			doctype,
			changes={
				"state": numbering.state(doctype),
				"series": wanted if wanted != was else None,
				"move": moves,
				"name_by": name_by,
				"rules": changed_rules,
				"summary": summary,
			},
			why=why,
		),
		"state": "Proposed",
		"next": "Tell them it applies to records made after they approve it, that records already made keep "
		"their names, and that the record's Settings › Numbering shows it.",
	}
