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

#: How any other kind may be named, as frappe's Customize Form offers it:
#: the naming rule it records, and what it writes as `autoname`. Frappe's
#: Autoincrement cannot be changed to or from once records exist, UUID
#: changes how the name is stored, and By script is code, so none is offered.
SERIES = "Naming Series"
FIELD = "Field"
EXPRESSION = "Expression"
#: The two kinds frappe's autoname spells as a word, as a person reads them.
WORDS = {"prompt": "Set by User", "hash": "Random"}
NAMING_RULE = {
	SERIES: 'By "Naming Series" field',
	FIELD: "By fieldname",
	EXPRESSION: "Expression (old style)",
	"prompt": "Set by user",
	"hash": "Random",
}
FIELD_KINDS = ("Data", "Link", "Select", "Int")

#: What a workspace administrator is given to write Naming Rules with.
GRANTS = {"Document Naming Rule": ("read", "write", "create", "delete")}


def _meta(doctype: str):
	"""The doctype, if how it is named is this workspace's to change."""
	roles.require()
	if not doctype or not frappe.db.exists("DocType", doctype):
		frappe.throw(_("There is no such kind of record."))
	meta = frappe.get_meta(doctype)
	if meta.istable or meta.issingle or meta.module in REFUSED_MODULES:
		frappe.throw(_("{0} is not named in a way this workspace sets.").format(_(doctype)))
	if not frappe.has_permission(doctype, "read"):
		frappe.throw(_("You cannot open {0}.").format(_(doctype)), frappe.PermissionError)
	return meta


def _series_meta(doctype: str):
	"""The doctype, if it also has the Naming Series field its series live in."""
	meta = _meta(doctype)
	if not meta.get_field("naming_series"):
		frappe.throw(_("{0} is not numbered by a series.").format(_(doctype)))
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
	_series_meta(doctype)
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
			"rules": [
				{**rule, "conditions": [dict(one) for one in rule["conditions"]]}
				for rule in naming_rules(doctype)
			],
		}
	)


@frappe.whitelist()
def series(doctype: Annotated[str, "The kind of record."]) -> list[dict]:
	"""Each series the doctype may be named by, the name it would give next,
	and the number it has reached. None for a kind with no series field."""
	if not _meta(doctype).get_field("naming_series"):
		return []
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

	_series_meta(doctype)
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
	_series_meta(doctype)
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
	_series_meta(doctype)
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


def _made_by_code(meta) -> bool:
	"""Whether records of the kind are made by code rather than by a person
	(a ledger, a log, One's own kinds), which names them as it expects to find
	them: frappe's User Cannot Create, or no create for whoever is asking."""
	return (
		bool(meta.in_create)
		or not frappe.has_permission(meta.name, "create")
		or frappe.db.get_value("Module Def", meta.module, "app_name") == "onedesk"
	)


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


def _by(meta) -> tuple[str, str]:
	"""How the doctype is named now, as (the choice, what `autoname` holds)."""
	autoname = (meta.autoname or "").strip()
	lowered = autoname.lower()
	if lowered.startswith("naming_series:"):
		return SERIES, SERIES
	if lowered.startswith("field:"):
		return FIELD, autoname
	if lowered == "prompt":
		return "prompt", "prompt"
	if lowered in ("", "hash"):
		return "hash", "hash"
	if "#" in autoname and ":" not in autoname and "." in autoname:
		return EXPRESSION, autoname
	return "", autoname


@frappe.whitelist()
def naming_by(doctype: Annotated[str, "The kind of record."]) -> dict | None:
	"""How a new record of a kind is named, and what else it may be named by.
	For the kinds that name themselves, their app's own choices; for any
	other, frappe's own: its series, one of its fields, an expression of its
	own, a name typed by whoever makes it, or a random one. None where there
	is no choice to make."""
	meta = _meta(doctype)
	if doctype in NAMED_BY:
		single, field, _method, _default = NAMED_BY[doctype]
		df = frappe.get_meta(single).get_field(field)
		value = frappe.db.get_single_value(single, field)
		return {
			"by": value,
			"value": value,
			"kinds": [{"value": one, "label": _(one)} for one in (df.options or "").split("\n") if one],
			"fields": [],
			"pattern": "",
			"app": True,
			# Auto Name falls back to the doctype's autoname, which is its series.
			"series": value in (SERIES, "Auto Name"),
		}
	if _names_itself(doctype) or (meta.autoname or "").lower() == "autoincrement" or _made_by_code(meta):
		return None
	by, value = _by(meta)
	fields = _fields(meta)
	kinds = [SERIES] if meta.get_field("naming_series") else []
	kinds += [FIELD] if fields else []
	kinds += [EXPRESSION, "prompt", "hash"]
	kinds = [{"value": one, "label": _(WORDS.get(one, one))} for one in kinds]
	if not by:
		# Named some other way (a newer expression, a UUID): kept until
		# something else is picked.
		by = value
		kinds.append({"value": value, "label": _("As {0} names it now").format(_(doctype))})
	return {
		"by": by,
		"value": value,
		"kinds": kinds,
		"fields": fields,
		"pattern": value if by == EXPRESSION else "",
		"app": False,
		"series": by == SERIES,
	}


def choices(said: dict) -> list[str]:
	"""Every value set_naming_by takes for a kind, bar an expression, which
	is written rather than picked."""
	return [one["value"] for one in said["kinds"] if one["value"] not in (FIELD, EXPRESSION)] + [
		one["value"] for one in said["fields"]
	]


def label(said: dict, value: str) -> str:
	"""A value set_naming_by takes, as a person reads it."""
	for one in said["kinds"] + said["fields"]:
		if one["value"] == value:
			return one["label"]
	return _(WORDS[value]) if value in WORDS else value


def check_pattern(doctype: str, pattern: str) -> None:
	"""An expression a new record is named by, checked as frappe checks one
	on a DocType: written as a series is, and its prefix no other kind's."""
	NamingSeries(pattern).validate()
	prefix = pattern.split(".", 1)[0]
	taken = frappe.get_all(
		"DocType", filters={"autoname": ["like", prefix + ".%"], "name": ["!=", doctype]}, pluck="name"
	) + frappe.get_all(
		"Property Setter",
		filters={"property": "autoname", "value": ["like", prefix + ".%"], "doc_type": ["!=", doctype]},
		pluck="doc_type",
	)
	if taken:
		frappe.throw(_("Series {0} already used in {1}").format(prefix, _(taken[0])))


@frappe.whitelist()
def preview_pattern(
	doctype: Annotated[str, "The kind of record."],
	pattern: Annotated[str, "An expression as it is being written."],
) -> dict:
	"""The name an expression being written would give next, or what is wrong
	with it."""
	from frappe.utils import strip_html

	_meta(doctype)
	pattern = (pattern or "").strip()
	if not pattern:
		return {}
	try:
		check_pattern(doctype, pattern)
	except frappe.ValidationError as e:
		frappe.clear_messages()
		return {"error": strip_html(str(e))}
	return _row(_settings(doctype), pattern)


@frappe.whitelist(methods=["POST"])
def set_naming_by(
	doctype: Annotated[str, "The kind of record."],
	value: Annotated[
		str,
		"Naming Series, field:<fieldname>, an expression such as PRJ-.YYYY.-.####, prompt (typed by whoever "
		"makes it), hash (random), or an app's own choice.",
	],
) -> dict | None:
	"""Change how a new record of a kind is named. For the kinds that name
	themselves, their app's own setting and its own method; for any other,
	frappe's `autoname` and naming rule as Customize Form writes them, with
	the series shown or hidden and a field made required and unique. Either
	way through property setters the workspace layer would otherwise refuse
	(layer.property_setter). Records already made keep their names."""
	said = naming_by(doctype)
	value = (value or "").strip()
	if not said or not value:
		frappe.throw(_("{0} cannot be named that way.").format(_(doctype)))
	if value == said["value"]:
		return said
	if said["app"]:
		if value not in choices(said):
			frappe.throw(_("{0} cannot be named that way.").format(_(doctype)))
		_set_app(doctype, value)
	else:
		if value not in choices(said):
			if value.startswith("field:") or value in (SERIES, "prompt", "hash"):
				frappe.throw(_("{0} cannot be named that way.").format(_(doctype)))
			check_pattern(doctype, value)
		_set_autoname(doctype, said["value"], value)
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


def _unique_already(doctype: str, fieldname: str) -> bool:
	return bool(frappe.db.get_value("DocField", {"parent": doctype, "fieldname": fieldname}, "unique"))


def _duplicates(doctype: str, fieldname: str) -> None:
	"""Refuse a field records already share, as frappe refuses marking it
	unique (DocType's check_unique_fields), before anything is written."""
	found = frappe.db.sql(
		f"""select `{fieldname}`, count(*) from `tab{doctype}` where ifnull(`{fieldname}`, '') != ''
		group by `{fieldname}` having count(*) > 1 limit 1"""
	)
	if found and found[0][0]:
		frappe.throw(
			_("{0} cannot name each {1}: two records already have {2} in it.").format(
				_(frappe.get_meta(doctype).get_label(fieldname)), _(doctype), found[0][0]
			)
		)


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

	by = value if value in (SERIES, "prompt", "hash") else FIELD if value.startswith("field:") else EXPRESSION
	field = value[6:] if by == FIELD else None
	left = was[6:] if was.startswith("field:") else None
	if field and frappe.db.has_column(doctype, field):
		_duplicates(doctype, field)
	schema = False
	frappe.flags.one_named_by = doctype
	try:
		put(None, "autoname", "naming_series:" if by == SERIES else value, "Data")
		put(None, "naming_rule", NAMING_RULE[by], "Data")
		if frappe.get_meta(doctype).get_field("naming_series"):
			put("naming_series", "hidden", 0 if by == SERIES else 1)
			put("naming_series", "reqd", 1 if by == SERIES else 0)
		if field:
			# Required and unique, as Customize Form marks a field a record is named by.
			put(field, "reqd", 1)
			if not _unique_already(doctype, field):
				put(field, "unique", 1)
				schema = True
		if left:
			# The field it was named by is as required and as unique as its app made it again.
			frappe.db.delete(
				"Property Setter",
				{
					"doc_type": doctype,
					"field_name": left,
					"property": ["in", ("reqd", "unique")],
					"is_system_generated": 0,
				},
			)
			schema = schema or not _unique_already(doctype, left)
	finally:
		frappe.flags.one_named_by = None
	if schema:
		# The unique index, added or dropped, as Customize Form's save does.
		frappe.clear_cache(doctype=doctype)
		frappe.db.updatedb(doctype)


# ------------------------------------------------------------------ naming rules


def settle() -> None:
	from onedesk.one import roles

	roles.grant(GRANTS)


def validate_rule(doc, method=None) -> None:
	"""Document Naming Rule validate: what a rule the workspace writes may do."""
	from onedesk.one import layer

	if layer.held():
		check_rule(doc)


#: How a rule's condition compares a field with its value: frappe's own.
COMPARISONS = ("=", "!=", ">", "<", ">=", "<=")


def check_rule(doc) -> None:
	"""A naming rule is on a kind of record Numbering covers, names by a plain
	prefix, and decides by the record's ordinary fields."""
	from onedesk.one import rules

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
		if row.condition not in COMPARISONS:
			frappe.throw(_("A rule compares with one of {0}.").format(" ".join(COMPARISONS)))


def naming_rules(doctype: str) -> list[dict]:
	"""A kind's naming rules, each with what it must match, highest priority
	first: as frappe tries them."""
	_meta(doctype)
	rows = frappe.get_list(
		"Document Naming Rule",
		filters={"document_type": doctype},
		fields=["name", "prefix", "prefix_digits", "priority", "disabled"],
		order_by="priority desc",
		limit_page_length=0,
	)
	matches = {}
	for one in frappe.get_all(
		"Document Naming Rule Condition",
		filters={"parenttype": "Document Naming Rule", "parent": ["in", [row.name for row in rows] or [""]]},
		fields=["parent", "field", "condition", "value"],
		order_by="idx asc",
	):
		matches.setdefault(one.parent, []).append(
			{"field": one.field, "condition": one.condition, "value": one.value}
		)
	return [dict(row, conditions=matches.get(row.name, [])) for row in rows]


def rule_doc(doctype: str, one: dict):
	"""A naming rule as a change describes it, new or an existing one of the
	kind with the change made, not saved: {name?, prefix, digits, priority,
	disabled, conditions: [{field, condition, value}]}."""
	if one.get("name"):
		doc = frappe.get_doc("Document Naming Rule", one["name"])
		if doc.document_type != doctype:
			frappe.throw(_("{0} is not a rule of {1}.").format(one["name"], _(doctype)))
	else:
		doc = frappe.new_doc("Document Naming Rule")
		doc.document_type = doctype
		doc.prefix_digits = 5
	for key, field in (("prefix", "prefix"), ("digits", "prefix_digits"), ("priority", "priority")):
		if one.get(key) is not None:
			doc.set(field, one[key])
	if one.get("disabled") is not None:
		doc.disabled = 1 if one["disabled"] else 0
	if one.get("conditions") is not None:
		doc.set("conditions", [])
		for row in one["conditions"]:
			doc.append(
				"conditions",
				{
					"field": row.get("field"),
					"condition": row.get("condition") or "=",
					"value": row.get("value"),
				},
			)
	check_rule(doc)
	doc.validate_fields_in_conditions()
	return doc
