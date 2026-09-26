"""Record Head: what a record's form says above its fields, as rows.

A form of ours used to say it in a script per doctype: an overview method
worked the numbers out, and the script drew them under the title and added
its buttons. Now a **Record Head** (one per doctype) holds the pill, the
sentence, the band of numbers and the verbs as rows, `onload` works them out
on the server as the reader, and one renderer (`public/js/head.js`) draws what
it sent. docs/SHELL.md, decision 4, is the argument.

What stays code is what is really a program, registered by name:

- a **measure** (`one_measures`) is a function of the record that answers one
  number or phrase, and may say its own label, tone and link. The arithmetic
  stays Python and tested; where it goes on the page is a row.
- a **verb** (`one_verbs`) is something done to the record: which doctypes it
  is for, when it can be done, what it asks, and what it does.
- a **chart** (`one_charts`) is a function of the record that answers a run
  of figures, drawn beside the band by frappe's own `frappe.Chart`: what this
  customer was billed month by month, what the asset is worth over its life.

A measure may also say how its number changed (`delta`) and how far it is to
a whole (`meter`), which the band draws as frappe's Number Card draws a change
and frappe-ui's Progress a part of a whole.

A row names only those, the record's own fields, and frappe's filters, so a
row cannot run anything. A count or a sum is taken with the reader's own list
permissions, so the band never shows a number the reader's list would not.

Each module declares its heads (`one_record_heads`) and `install` writes them
on every migrate, as notification types are.
"""

import json
import re
from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import cstr, flt
from frappe.utils.data import evaluate_filters

from onedesk.one import linked

CACHE = "one_record_heads"
SOURCES = ("Field", "Linked Field", "Count", "Sum", "Measure")
TONES = ("", "quiet", "waiting", "alarm")
SLOT = re.compile(r"\{\{\s*doc\.([a-z0-9_]+)\s*\}\}")


# ------------------------------------------------------------------ what modules register


def _merged(hook: str) -> dict:
	found = {}
	for path in frappe.get_hooks(hook) or []:
		found.update(frappe.get_attr(path))
	return found


def measures() -> dict:
	"""Every measure, by name: a function of the record."""
	return _merged("one_measures")


def verbs() -> dict:
	"""Every verb, by name: `doctypes`, `label`, `when`, `fields`, `title`,
	`action` and `run`. `label` and `title` may be functions of the record."""
	return _merged("one_verbs")


def charts() -> dict:
	"""Every chart, by name: `doctypes`, `label` and `figures`, a function of
	the record that answers what is drawn, or None when there is nothing to
	draw. The figures are worked out as the reader, like a measure's."""
	return _merged("one_charts")


def declared() -> list[dict]:
	"""Every head the modules declare, each with the module that declared it."""
	found = []
	for path in frappe.get_hooks("one_record_heads") or []:
		module = path.split(".")[1]
		found.extend({**head, "module": module} for head in frappe.get_attr(path))
	return found


# ------------------------------------------------------------------ pure


def slots(template: str) -> list[str]:
	"""The record's fields a template names. Pure."""
	return SLOT.findall(template or "")


def fill(template: str, values: dict, *, url: bool = False) -> str:
	"""A template with each `{{ doc.field }}` replaced by the record's value,
	quoted for a link when `url`. Nothing else in it is read. Pure."""

	def value(match):
		said = cstr(values.get(match.group(1)))
		return quote(said, safe="") if url else said

	return SLOT.sub(value, template or "")


def conditions(text: str | None) -> list:
	"""A row's Shown When, read. Empty is always. Pure."""
	if not (text or "").strip():
		return []
	read = json.loads(text)
	if isinstance(read, dict):
		read = [[key, "=", value] for key, value in read.items()]
	if not isinstance(read, list):
		raise ValueError("not a list of filters")
	return read


def holds(doc, text: str | None) -> bool:
	"""Whether a row's condition holds for the record."""
	found = conditions(text)
	return not found or evaluate_filters(doc, found)


def counting(text: str | None, doc) -> list:
	"""A count's or a sum's filters, with the record's values in them."""
	return [[*row[:-1], fill(row[-1], doc)] if isinstance(row[-1], str) else row for row in conditions(text)]


# ------------------------------------------------------------------ the rows, checked


def validate(head) -> None:
	"""A head names only its own record's fields, registered measures and
	verbs, and filters that read. Called by Record Head's validate."""
	meta = frappe.get_meta(head.record_doctype)
	known = {"name", "owner", "creation", "modified", "docstatus", *(df.fieldname for df in meta.fields)}

	def field(name, where):
		if name not in known:
			frappe.throw(
				_("{0} names {1}, which {2} does not have.").format(where, name, _(head.record_doctype))
			)

	def filters(text, where):
		try:
			conditions(text)
		except ValueError:
			frappe.throw(_("{0} is not a list of filters.").format(where))

	def template(text, where):
		for name in slots(text):
			field(name, where)

	for row in head.indicators:
		if row.get("measure") and row.measure not in measures():
			frappe.throw(
				_("Indicator {0} names the measure {1}, which no module has.").format(row.idx, row.measure)
			)
		filters(row.shown_when, _("Indicator {0}").format(row.idx))
	for row in head.sentences:
		filters(row.shown_when, _("Sentence {0}").format(row.idx))
		template(row.text, _("Sentence {0}").format(row.idx))
	for row in head.band:
		where = _("Band row {0}").format(row.idx)
		filters(row.shown_when, where)
		template(row.route, where)
		if row.source not in SOURCES:
			frappe.throw(_("{0} takes its value from nowhere.").format(where))
		if row.source in ("Field", "Linked Field"):
			field(row.link_field if row.source == "Linked Field" else row.field, where)
		if row.source == "Linked Field":
			df = meta.get_field(row.link_field)
			if df.fieldtype != "Link":
				frappe.throw(_("{0} goes through {1}, which is not a link.").format(where, row.link_field))
			if not frappe.get_meta(df.options).has_field(row.field):
				frappe.throw(
					_("{0} names {1}, which {2} does not have.").format(where, row.field, _(df.options))
				)
		if row.source in ("Count", "Sum"):
			if not row.of_doctype:
				frappe.throw(_("{0} counts nothing.").format(where))
			filters(row.filters, where)
			for one in conditions(row.filters):
				if isinstance(one[-1], str):
					template(one[-1], where)
		if row.source == "Sum" and not frappe.get_meta(row.of_doctype).has_field(row.field):
			frappe.throw(
				_("{0} sums {1}, which {2} does not have.").format(where, row.field, _(row.of_doctype))
			)
		if row.source == "Measure" and row.measure not in measures():
			frappe.throw(_("{0} names the measure {1}, which no module has.").format(where, row.measure))
	linked.validate(head)
	registered = verbs()
	for row in head.verbs:
		verb = registered.get(row.verb)
		if not verb:
			frappe.throw(_("Verb {0} is {1}, which no module has.").format(row.idx, row.verb))
		if head.record_doctype not in verb["doctypes"]:
			frappe.throw(_("{0} is not something done to {1}.").format(row.verb, _(head.record_doctype)))
	drawn = charts()
	for row in head.get("charts") or []:
		filters(row.shown_when, _("Chart {0}").format(row.idx))
		chart = drawn.get(row.chart)
		if not chart:
			frappe.throw(_("Chart {0} is {1}, which no module has.").format(row.idx, row.chart))
		if head.record_doctype not in chart["doctypes"]:
			frappe.throw(_("{0} is not a chart of {1}.").format(row.chart, _(head.record_doctype)))


# ------------------------------------------------------------------ what the form is sent


def headed() -> set[str]:
	"""The doctypes with a head, cached until one changes."""
	held = frappe.cache.get_value(CACHE)
	if held is None:
		held = frappe.get_all("Record Head", filters={"enabled": 1}, pluck="record_doctype")
		frappe.cache.set_value(CACHE, held)
	return set(held)


def onload(doc, method=None) -> None:
	"""The head of a saved record, worked out as the reader."""
	if doc.is_new() or doc.doctype not in headed():
		return
	doc.set_onload("one_head", said(doc, frappe.get_cached_doc("Record Head", doc.doctype)))


def said(doc, head) -> dict:
	"""What the head says of this record."""
	indicator = next(
		(said for row in head.indicators if holds(doc, row.shown_when) and (said := _indicator(doc, row))),
		None,
	)
	sentence = next((row for row in head.sentences if holds(doc, row.shown_when)), None)
	return {
		"indicator": indicator,
		"sentence": sentence and {"text": fill(_(sentence.text), _Formatted(doc)), "colour": sentence.colour},
		# A measure may answer several numbers (one per leave type); each is
		# a stat of its own.
		"band": [stat for row in head.band if holds(doc, row.shown_when) for stat in _stats(doc, row)],
		"verbs": [verb for row in head.verbs if (verb := _verb(doc, row))],
		"charts": [
			chart
			for row in head.get("charts") or []
			if holds(doc, row.shown_when) and (chart := _chart(doc, row))
		],
		"linked": linked.loaded(doc, head),
	}


class _Formatted:
	"""The record's values as the reader reads them, for a sentence."""

	def __init__(self, doc):
		self.doc = doc

	def get(self, key, default=None):
		return self.doc.get_formatted(key) if self.doc.meta.has_field(key) else self.doc.get(key, default)


def _indicator(doc, row) -> dict | None:
	"""The pill: the row's own label and colour, or what its measure says of
	the record (where a person is today), or nothing when it says nothing."""
	if not row.get("measure"):
		return {"label": _(row.label), "colour": row.colour}
	measure = measures().get(row.measure)
	said = measure(doc) if measure else None
	return {"label": said["label"], "colour": said.get("colour") or "gray"} if said else None


def _stats(doc, row) -> list[dict]:
	if row.source == "Measure" and (measure := measures().get(row.measure)):
		said = measure(doc)
		if isinstance(said, list):
			return [stat for one in said if (stat := _stat(doc, row, one))]
		stat = _stat(doc, row, said)
	else:
		stat = _stat(doc, row)
	return [stat] if stat else []


def _stat(doc, row, measured=None) -> dict | None:
	stat = {"label": _(row.label), "route": fill(row.route, doc, url=True) or None, "tone": row.tone or None}
	value = measured if row.source == "Measure" else _value(doc, row)
	# A measure with nothing to say of this record is not shown.
	if row.source == "Measure" and value is None:
		return None
	if isinstance(value, dict):
		# A measure may say how it changed (`delta`) and how far it is to a
		# whole (`meter`), which the band draws as a metric card does.
		# A time since goes as the moment (`when`), for the desk to say.
		stat.update(
			{
				key: value[key]
				for key in ("label", "route", "tone", "delta", "meter", "when", "short")
				if key in value
			}
		)
		value = value.get("value")
	if value in (None, ""):
		if row.hide_empty:
			return None
		value, stat["tone"] = "—", stat["tone"] or "quiet"
	elif row.hide_empty and value == 0:
		return None
	stat["value"] = cstr(value)
	return stat


def _value(doc, row):
	if row.source == "Field":
		return doc.get_formatted(row.field) if doc.get(row.field) not in (None, "") else None
	if row.source == "Linked Field":
		target = doc.get(row.link_field)
		through = doc.meta.get_field(row.link_field).options
		if not target or not frappe.has_permission(through, "read", target):
			return None
		value = frappe.db.get_value(through, target, row.field)
		df = frappe.get_meta(through).get_field(row.field)
		return frappe.format_value(value, df) if value not in (None, "") else None
	if row.source == "Count":
		if not frappe.has_permission(row.of_doctype, "read"):
			return None
		found = frappe.get_list(
			row.of_doctype, filters=counting(row.filters, doc), fields=[{"COUNT": "*", "as": "n"}]
		)
		return found[0].n if found else 0
	if row.source == "Sum":
		if not frappe.has_permission(row.of_doctype, "read"):
			return None
		found = frappe.get_list(
			row.of_doctype, filters=counting(row.filters, doc), fields=[{"SUM": row.field, "as": "total"}]
		)
		total = found[0].total if found else 0
		return frappe.format_value(total or 0, frappe.get_meta(row.of_doctype).get_field(row.field))
	measure = measures().get(row.measure)
	return measure(doc) if measure else None


#: How a chart may be drawn: frappe.Chart's own types, and a heat map of
#: named days (a quarter of attendance), whose squares are frappe-charts'
#: geometry and whose colours mean a state rather than an amount.
KINDS = ("bar", "line", "heat")


def _chart(doc, row) -> dict | None:
	"""A registered chart's figures for this record: labels along the bottom
	and one value each, how to format them, and a line saying what they add
	up to. Nothing when it has nothing to show."""
	chart = charts().get(row.chart)
	if not chart or doc.doctype not in chart["doctypes"]:
		return None
	figures = chart["figures"](doc)
	if figures and figures.get("kind") == "heat":
		return (
			{
				"label": _(row.label) if row.label else cstr(_said_of(chart["label"], doc)),
				"kind": "heat",
				"days": figures["days"],
			}
			if figures.get("days")
			else None
		)
	if not figures or not any(flt(value) for value in figures.get("values") or []):
		return None
	return {
		"label": _(row.label) if row.label else cstr(_said_of(chart["label"], doc)),
		"kind": figures.get("kind") if figures.get("kind") in KINDS else "bar",
		"labels": [cstr(one) for one in figures["labels"]],
		"values": [flt(one) for one in figures["values"]],
		"currency": figures.get("currency"),
		"said": figures.get("said"),
		"route": figures.get("route"),
		"marked": figures.get("marked"),
	}


def _said_of(value, doc):
	return value(doc) if callable(value) else value


def _verb(doc, row) -> dict | None:
	verb = verbs().get(row.verb)
	if not verb or doc.doctype not in verb["doctypes"] or not verb["when"](doc):
		return None
	label = _(row.label) if row.label else cstr(_said_of(verb["label"], doc))
	return {
		"verb": row.verb,
		"label": label,
		"primary": bool(row.primary),
		"title": cstr(_said_of(verb.get("title"), doc) or label),
		"action": cstr(_said_of(verb.get("action"), doc) or label),
		"fields": verb["fields"](doc) if verb.get("fields") else [],
	}


@frappe.whitelist(methods=["POST"])
def run(doctype: str, name: str, verb: str, values: dict | str | None = None) -> str:
	"""Do a verb the record's head offers, if it still can be done."""
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("read")
	if doctype not in headed() or verb not in {
		row.verb for row in frappe.get_cached_doc("Record Head", doctype).verbs
	}:
		frappe.throw(_("{0} is not offered here.").format(verb), frappe.PermissionError)
	found = verbs().get(verb)
	if not found or not found["when"](doc):
		frappe.throw(_("This cannot be done to {0} now.").format(name))
	values = frappe.parse_json(values) or {}
	return found["run"](doc, **values) or _("Done.")


# ------------------------------------------------------------------ written on migrate


TABLES = ("indicators", "sentences", "band", "verbs", "charts", "linked")


def install() -> None:
	"""Each module's heads, as it declares them. The rows a workspace added
	(`custom`) are its own and stay; a head a module no longer declares loses
	the module's rows, and goes when nothing of the workspace's is left."""
	wanted = {}
	for head in declared():
		wanted[head["doctype"]] = head
		_write(head)
	for name in frappe.get_all("Record Head", filters={"module": ["is", "set"]}, pluck="name"):
		if name not in wanted:
			_write({"doctype": name, "module": None})
	frappe.cache.delete_value(CACHE)


def _write(head: dict) -> None:
	if not frappe.db.exists("DocType", head["doctype"]):
		return
	doc = (
		frappe.get_doc("Record Head", head["doctype"])
		if frappe.db.exists("Record Head", head["doctype"])
		else frappe.new_doc("Record Head")
	)
	kept = {table: [row for row in doc.get(table) if row.custom] for table in TABLES}
	if not doc.is_new() and not head.get("module") and not any(kept.values()):
		frappe.delete_doc("Record Head", doc.name, ignore_permissions=True, force=True)
		return
	doc.update({"record_doctype": head["doctype"], "module": head["module"], "enabled": 1})
	for table in TABLES:
		doc.set(table, [])
		for row in head.get(table) or []:
			row = dict(row)
			for key in ("label", "text"):
				if key in row:
					row[key] = getattr(row[key], "msg", None) or row[key]
			for key in ("shown_when", "filters"):
				if not isinstance(row.get(key, ""), str):
					row[key] = json.dumps(row[key])
			doc.append(table, row)
		# The workspace's own rows come after the module's.
		for row in kept[table]:
			doc.append(table, row)
	doc.flags.ignore_permissions = True
	doc.save()
