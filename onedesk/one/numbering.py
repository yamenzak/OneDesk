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
	return frappe.as_json({row["series"]: row["current"] for row in series(doctype)})


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
