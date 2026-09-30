"""Numbering: the series a workspace's documents are named by, INV-2026-0001
and the like, for its administrators.

Frappe keeps this in Document Naming Settings, a Single whose whitelisted
methods change any doctype's series and run for anybody who can read it
(`run_doc_method` checks read, and `update_series` writes the property
setters itself). So the workspace administrator is not given that Single.
These are the doors instead, each guarded to a doctype the workspace may
change and its administrator may read, and each calling frappe's own logic:
`update_series` validates a series and refuses one another doctype uses,
`NamingSeries` previews and counts. docs/DESK-COVERAGE.md, stage 2.

The one thing frappe lets its System Managers do that this does not: set a
series' next number lower. Going down repeats a number already used, and the
save that meets it fails; going up only skips numbers, as a new year does.
"""

from typing import Annotated

import frappe
from frappe import _
from frappe.model.naming import NamingSeries, parse_naming_series
from frappe.query_builder.functions import Length, Max
from frappe.utils import cint

from onedesk.one import roles
from onedesk.one.customize import REFUSED_MODULES

SETTINGS = "Document Naming Settings"

#: Kinds of record that name themselves in code, by one of their app's own
#: settings: the Single, the field, the method that shows or hides the series
#: and the name field to match (or None), and whether the code reads the
#: setting as a global default, which the Single's save would have written.
NAMED_BY = {
	"Customer": ("Selling Settings", "cust_master_name", "update_customer_naming_settings", True),
	"Supplier": ("Buying Settings", "supp_master_name", "update_supplier_naming_settings", True),
	"Item": ("Stock Settings", "item_naming_by", "update_item_naming_settings", True),
	"Employee": ("HR Settings", "emp_created_by", "set_naming_series", False),
	"Campaign": ("CRM Settings", "campaign_naming_by", None, True),
}

#: What any other kind may be named by: its series, or a field a person fills.
SERIES = "Naming Series"
FIELD_KINDS = ("Data", "Link", "Select", "Int")

#: What a workspace administrator is given to write Naming Rules with.
GRANTS = {"Document Naming Rule": ("read", "write", "create", "delete")}


def _meta(doctype: str):
	"""The doctype, if its numbering is this workspace's to change."""
	roles.require()
	if not doctype or not frappe.db.exists("DocType", doctype):
		frappe.throw(_("There is no such kind of record."))
	meta = frappe.get_meta(doctype)
	if meta.istable or meta.issingle or meta.module in REFUSED_MODULES or not meta.get_field("naming_series"):
		frappe.throw(_("{0} is not numbered by a series this workspace sets.").format(_(doctype)))
	if not frappe.has_permission(doctype, "read"):
		frappe.throw(_("You cannot open {0}.").format(_(doctype)), frappe.PermissionError)
	return meta


def _settings(doctype: str):
	settings = frappe.get_single(SETTINGS)
	settings.transaction_type = doctype
	return settings


def _options(settings) -> list[str]:
	return settings.get_options_list(settings.get_options() or "")


def _row(settings, one: str) -> dict:
	"""A series, the number it has reached and the name it gives next. Frappe's
	preview counts from one whatever the series has reached, so the next name is
	parsed here with the real next number, from the same parser."""
	counter = NamingSeries(one)
	current = counter.get_current_value()
	try:
		following = parse_naming_series(
			counter.series,
			doc=settings._fetch_last_doc_if_available(),
			number_generator=lambda _prefix, digits: str(current + 1).zfill(digits),
		)
	except Exception:
		frappe.clear_last_message()
		settings.try_naming_series = one
		following = (settings.preview_series() or "").split("\n")[0]
	return {"series": one, "next": following, "current": current, **used(settings.transaction_type, counter)}


def used(doctype: str, counter) -> dict:
	"""The highest number records of the doctype already carry under the
	series' prefix as it stands today, read from their names: what a counter
	moved below it would repeat. A name of the prefix and exactly the series'
	digits is one it gave; an amendment's `-1` is longer and not counted, and
	a wildcard in the prefix only widens what the digits check then narrows."""
	prefix = counter.get_prefix()
	digits = counter.series.count("#")
	table = frappe.qb.DocType(doctype)
	found = (
		frappe.qb.from_(table)
		.select(Max(table.name))
		.where(table.name.like(prefix + "%"))
		.where(Length(table.name) == len(prefix) + digits)
	).run()
	highest = found[0][0] if found and found[0][0] else None
	number = cint(highest[len(prefix) :]) if highest and highest[len(prefix) :].isdigit() else 0
	return {"used": number, "last_name": highest if number else None}


def check(doctype: str, options: list[str]) -> None:
	"""Whether a list of series would be taken, without taking it: frappe's
	own checks, a series written as frappe reads one and not another
	doctype's."""
	_meta(doctype)
	for one in options:
		NamingSeries(one).validate()
	settings = _settings(doctype)
	settings.naming_series_options = "\n".join(options)
	settings.check_duplicate()


def state(doctype: str) -> str:
	"""What the doctype's numbering is now, so a change suggested against an
	older one is refused."""
	said = naming_by(doctype)
	return frappe.as_json(
		{
			"series": {row["series"]: row["current"] for row in series(doctype)},
			"named_by": said and said["value"],
		}
	)


@frappe.whitelist()
def series(doctype: Annotated[str, "The kind of record."]) -> list[dict]:
	"""Each series the doctype may be named by, the name it would give next,
	and the number it has reached."""
	_meta(doctype)
	settings = _settings(doctype)
	return [_row(settings, one) for one in _options(settings)]


@frappe.whitelist()
def preview(
	doctype: Annotated[str, "The kind of record."],
	one: Annotated[str, "A series as it is being written."],
) -> dict:
	"""The name a series being written would give next, or what frappe would
	say is wrong with it, while it is typed in the Add Series window."""
	from frappe.utils import strip_html

	_meta(doctype)
	one = (one or "").strip()
	if not one:
		return {}
	settings = _settings(doctype)
	try:
		NamingSeries(one).validate()
		if one not in _options(settings):
			settings.naming_series_options = one
			settings.check_duplicate()
	except frappe.ValidationError as e:
		frappe.clear_messages()
		return {"error": strip_html(str(e))}
	return {**_row(_settings(doctype), one), "mine": one in _options(settings)}


@frappe.whitelist(methods=["POST"])
def save(
	doctype: Annotated[str, "The kind of record."],
	options: Annotated[str | list, "Every series it may be named by, the default first."],
) -> list[dict]:
	"""The doctype's series, as a whole list. Frappe's own `update_series`
	validates each and refuses one another doctype already uses."""
	_meta(doctype)
	wanted = [one.strip() for one in (frappe.parse_json(options) or []) if one and one.strip()]
	if not wanted:
		frappe.throw(_("A kind of record numbered by a series needs at least one."))
	settings = _settings(doctype)
	settings.naming_series_options = "\n".join(wanted)
	frappe.flags.one_numbering = True
	try:
		settings.update_series()
	finally:
		frappe.flags.one_numbering = False
	frappe.clear_messages()
	return series(doctype)


@frappe.whitelist(methods=["POST"])
def set_current(
	doctype: Annotated[str, "The kind of record."],
	one: Annotated[str, "The series."],
	current: Annotated[int, "The number the series has reached; the next name continues after it."],
) -> list[dict]:
	"""Move a series on, as frappe's `update_series_start` does, and keep the
	change in its Version log the same way. Never back: see the module."""
	_meta(doctype)
	settings = _settings(doctype)
	if one not in _options(settings):
		frappe.throw(_("{0} is not a series of {1}.").format(one, _(doctype)))
	counter = NamingSeries(one)
	was = counter.get_current_value()
	current = cint(current)
	reached = used(doctype, counter)["used"]
	if current < reached:
		frappe.throw(
			_("{0} goes up to {1} already, so it can only be moved to {1} or more.").format(one, reached)
		)
	if current < was:
		frappe.throw(
			_(
				"{0} has reached {1}. It can only go up: a lower number would repeat a name already used."
			).format(one, was)
		)
	if current != was:
		counter.update_counter(current)
		settings.create_version_log_for_change(counter.get_prefix(), was, current)
	return series(doctype)


def doctypes() -> list[dict]:
	"""Every kind of record this administrator may renumber, with the series
	it uses by default and the name that would come next: Workspace >
	Numbering."""
	roles.require()
	named = set(
		frappe.get_all(
			"DocField", filters={"fieldname": "naming_series", "parenttype": "DocType"}, pluck="parent"
		)
	)
	named |= set(frappe.get_all("Custom Field", filters={"fieldname": "naming_series"}, pluck="dt"))
	rows = []
	for doctype in sorted(named):
		meta = frappe.get_meta(doctype)
		if meta.istable or meta.issingle or meta.module in REFUSED_MODULES:
			continue
		if not frappe.has_permission(doctype, "read"):
			continue
		settings = _settings(doctype)
		options = _options(settings)
		if not options:
			continue
		first = _row(settings, options[0])
		rows.append(
			{
				"doctype": doctype,
				"label": _(doctype),
				"module": meta.module,
				"series": first["series"],
				"next": first["next"],
				"others": len(options) - 1,
			}
		)
	return sorted(rows, key=lambda one: one["label"])


# ------------------------------------------------------------------ named by


def _names_itself(doctype: str) -> bool:
	"""Whether a kind of record is named by its own code, which a changed
	`autoname` would not reach."""
	from frappe.model.base_document import get_controller

	return hasattr(get_controller(doctype), "autoname")


def _fields(meta) -> list[dict]:
	"""The fields a new record could be named by: one a person fills in, on
	the form, that every reader of the record may see."""
	return [
		{"value": f"field:{df.fieldname}", "label": _(df.label)}
		for df in meta.fields
		if df.fieldtype in FIELD_KINDS
		and df.fieldname not in ("naming_series", "amended_from")
		and df.label
		and not df.hidden
		and not df.permlevel
		and not df.is_virtual
		and (not df.read_only or df.fetch_from)
	]


@frappe.whitelist()
def naming_by(doctype: Annotated[str, "The kind of record."]) -> dict | None:
	"""How a new record of a kind is named, and what else it may be named by:
	its app's own setting for the kinds that name themselves, else its series
	or one of its fields. None where there is no choice."""
	meta = _meta(doctype)
	if doctype in NAMED_BY:
		single, field, _method, _default = NAMED_BY[doctype]
		df = frappe.get_meta(single).get_field(field)
		return {
			"value": frappe.db.get_single_value(single, field),
			"options": [{"value": one, "label": _(one)} for one in (df.options or "").split("\n") if one],
			"by_field": False,
		}
	if _names_itself(doctype):
		return None
	autoname = meta.autoname or ""
	options = [{"value": SERIES, "label": _(SERIES)}, *_fields(meta)]
	value = SERIES if autoname.startswith("naming_series:") else autoname
	if value not in [one["value"] for one in options]:
		# Named some other way by its app (a fixed series, an expression): kept
		# until something else is picked.
		options.append({"value": value, "label": _("As {0} names it now").format(_(doctype))})
	return {"value": value, "options": options, "by_field": True}


@frappe.whitelist(methods=["POST"])
def set_naming_by(
	doctype: Annotated[str, "The kind of record."],
	value: Annotated[
		str, "One of the values naming_by lists: Naming Series, field:<fieldname>, or an app's choice."
	],
) -> dict | None:
	"""Change how a new record of a kind is named. For the kinds that name
	themselves, their app's own setting and its own method; for any other,
	frappe's `autoname` as Customize Form writes it, with the series shown or
	hidden and the field made required. Either way through property setters
	the workspace layer would otherwise refuse (layer.property_setter)."""
	said = naming_by(doctype)
	if not said or value not in [one["value"] for one in said["options"]]:
		frappe.throw(_("{0} cannot be named that way.").format(_(doctype)))
	if value == said["value"]:
		return said
	if not said["by_field"]:
		_set_app(doctype, value)
	elif value == SERIES or value.startswith("field:"):
		_set_autoname(doctype, said["value"], value)
	else:
		frappe.throw(_("{0} cannot be named that way.").format(_(doctype)))
	frappe.clear_cache(doctype=doctype)
	return naming_by(doctype)


def _set_app(doctype: str, value: str) -> None:
	single, field, method, default = NAMED_BY[doctype]
	settings = frappe.get_single(single)
	settings.set(field, value)
	frappe.flags.one_named_by = doctype
	try:
		if method:
			getattr(settings, method)()
	finally:
		frappe.flags.one_named_by = None
	settings.db_set(field, value)
	if default:
		frappe.db.set_default(field, value)


def _set_autoname(doctype: str, was: str, value: str) -> None:
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter

	def put(field, prop, one, kind="Check"):
		make_property_setter(
			doctype,
			field,
			prop,
			one,
			kind,
			for_doctype=not field,
			validate_fields_for_doctype=False,
			is_system_generated=False,
		)

	by_field = value.startswith("field:")
	frappe.flags.one_named_by = doctype
	try:
		put(None, "autoname", "naming_series:" if not by_field else value, "Data")
		put(None, "naming_rule", "By fieldname" if by_field else 'By "Naming Series" field', "Data")
		put("naming_series", "hidden", 1 if by_field else 0)
		put("naming_series", "reqd", 0 if by_field else 1)
		if by_field:
			put(value[6:], "reqd", 1)
		if was.startswith("field:"):
			# The field it was named by is as required as its app made it again.
			frappe.db.delete(
				"Property Setter",
				{"doc_type": doctype, "field_name": was[6:], "property": "reqd", "is_system_generated": 0},
			)
	finally:
		frappe.flags.one_named_by = None


# ------------------------------------------------------------------ naming rules


def settle() -> None:
	from onedesk.one import roles

	roles.grant(GRANTS)


def validate_rule(doc, method=None) -> None:
	"""Document Naming Rule validate: a rule the workspace writes is on a kind of
	record Numbering covers, names by a plain prefix, and decides by the
	record's ordinary fields."""
	from onedesk.one import layer, rules

	if not layer.held():
		return
	_meta(doc.document_type)
	prefix = (doc.prefix or "").strip()
	if not prefix or "#" in prefix:
		frappe.throw(_("A rule's prefix is the text before the number, such as RET-.YYYY.-"))
	NamingSeries(prefix + ".#").validate()
	if not 1 <= cint(doc.prefix_digits) <= 10:
		frappe.throw(_("A rule's number has between 1 and 10 digits."))
	allowed = set(rules.readable(doc.document_type))
	for row in doc.conditions or []:
		if row.field not in allowed:
			frappe.throw(
				_("A rule can only look at an ordinary field of the record, not {0}.").format(row.field)
			)
