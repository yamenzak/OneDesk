"""A workspace with one company is never asked which.

Every `Company` Link is hidden and filled by the global default, worked out
from the site's own schema after every migrate and whenever a company is
added or deleted. Once there is a second company, the record types a module
has made ready for several (`ready.MODULES[...]["companies"]`) show it, as a
column and a filter, defaulted by ERPNext to the reader's company.
"""

import frappe

FIELD = "company"
OFF = (("hidden", "1"), ("in_list_view", "0"), ("in_standard_filter", "0"))
ON = (("in_list_view", "1"), ("in_standard_filter", "1"))
PROPS = ("hidden", "in_list_view", "in_standard_filter", "default")


def several() -> bool:
	return frappe.db.count("Company") > 1


def reader_company() -> str | None:
	"""The company the reader works in: their own default, else the
	workspace's (erpnext.get_default_company). Every figure, Home and new
	record follows it."""
	from erpnext import get_default_company

	return get_default_company()


def workspace_company() -> str | None:
	"""The workspace's own default company, else the first there is, whoever
	reads: for what belongs to the workspace rather than to one reader."""
	return frappe.defaults.get_global_default("company") or frappe.db.get_value("Company", {}, "name")


def company_currency(company: str | None = None) -> str | None:
	"""A company's own currency, the reader's company's when none is named;
	None with no company at all."""
	from erpnext import get_company_currency

	company = company or reader_company()
	return get_company_currency(company) if company else None


def ready() -> set[str]:
	"""The record types every module has made ready for several companies."""
	from onedesk.one.ready import MODULES

	return {doctype for spec in MODULES.values() for doctype in spec.get("companies", ())}


def hide(*_args) -> None:
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter

	shown = ready() if several() else set()
	fields = _fields()
	for field in fields:
		parent = field["parent"]
		if parent in shown:
			frappe.db.delete(
				"Property Setter",
				{"doc_type": parent, "field_name": FIELD, "property": ["in", PROPS], "is_system_generated": 1},
			)
		wanted = () if parent in shown and field.get("istable") else ON if parent in shown else OFF
		for prop, value in wanted:
			if field.get(prop) == int(value) or _written(parent, prop) or _holds(parent, prop, value):
				continue
			make_property_setter(parent, FIELD, prop, value, "Check", validate_fields_for_doctype=False)
	_defaults(make_property_setter, [field for field in fields if field["parent"] not in shown])
	frappe.clear_cache()


def mine() -> dict | None:
	"""The companies the reader may work in, the one they work in now, and the
	record types whose lists open on it, for the frame's switch and the lists
	(list.js); None with only one, so nothing shows."""
	names = frappe.get_list("Company", pluck="name", order_by="name asc", limit_page_length=0, ignore_permissions=False)
	if len(names) < 2:
		return None
	now = reader_company()
	return {"current": now if now in names else names[0], "all": names, "doctypes": sorted(ready())}


@frappe.whitelist(methods=["POST"])
def use(company: str) -> None:
	"""Work in another company: the reader's default, which every Home,
	figure and new record follows."""
	if company not in ((mine() or {}).get("all") or ()):
		raise frappe.PermissionError
	frappe.defaults.set_user_default("company", company)


def changed(doc=None, method=None) -> None:
	"""A company added or deleted, or the default company changed: the fields
	follow, after the commit."""
	frappe.enqueue("onedesk.one.company.hide", queue="short", enqueue_after_commit=True, deduplicate=True, job_id="one_company_fields")


def _defaults(make_property_setter, fields: list[dict]) -> None:
	"""The company as the default of every hidden mandatory Company field, and
	again when the workspace's default company changes or is gone."""
	company = frappe.defaults.get_global_default("company")
	if not company or not frappe.db.exists("Company", company):
		return
	for field in fields:
		if not field.get("reqd") or field.get("default"):
			continue
		said = frappe.db.get_value(
			"Property Setter", {"doc_type": field["parent"], "field_name": FIELD, "property": "default"}, "value"
		)
		if said == company:
			continue
		make_property_setter(
			field["parent"], FIELD, "default", company, "Text", validate_fields_for_doctype=False
		)


def _fields() -> list[dict]:
	"""Every Company Link called `company`, standard and custom alike."""
	where = {"fieldname": FIELD, "fieldtype": "Link", "options": "Company"}
	columns = ["hidden", "in_list_view", "in_standard_filter", "reqd", "default"]
	standard = frappe.get_all("DocField", filters=where, fields=["parent", *columns])
	custom = frappe.get_all(
		"Custom Field",
		filters=where,
		fields=["dt as parent", *columns],
	)
	tables = set(frappe.get_all("DocType", filters={"istable": 1}, pluck="name"))
	return [dict(field, istable=field["parent"] in tables) for field in standard + custom]


def _holds(doctype: str, prop: str, value: str) -> bool:
	"""Whether our own setter already says this, so it is not made again: a new
	Property Setter deletes the one it replaces, and every delete queues a job."""
	return bool(
		frappe.db.exists(
			"Property Setter",
			{"doc_type": doctype, "field_name": FIELD, "property": prop, "value": value},
		)
	)


def _written(doctype: str, prop: str) -> bool:
	"""Whether anybody has already set this property, us or the tenant.

	Same rule as `policy.seed`: a workspace that deliberately put the field back
	keeps it, because a default that reasserts itself every migrate is not a
	default.
	"""
	return bool(
		frappe.db.exists(
			"Property Setter",
			{"doc_type": doctype, "field_name": FIELD, "property": prop, "is_system_generated": 0},
		)
	)


def frame_colour() -> str | None:
	"""The workspace's Frame Colour (One's ControlCenter › Branding), for the
	rail and the bars around every screen; None is One's own."""
	company = frappe.defaults.get_global_default("company")
	return frappe.get_cached_value("Company", company, "one_frame_colour") if company else None


def frame_ink(colour: str | None) -> str | None:
	"""The ink that reads on the Frame Colour, by the rule the letter heads
	use for text on the Brand Colour (letter_heads.on): "light", or "dark"
	where white would not stand out. None for One's own frame."""
	if not colour:
		return None
	from onedesk.one_studio import letter_heads

	return "light" if letter_heads.on(colour) == "#ffffff" else "dark"
