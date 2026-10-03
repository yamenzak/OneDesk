"""Record types: kinds of record a workspace keeps of its own, beside the
ones its apps came with. A gym's memberships, a school's terms, a fleet's
vehicles.

A record type is frappe's own custom DocType (`custom`, module One Studio),
with a **Record Type** of ours beside it that the administrator reads: what
it is for, the app it belongs to, who asked. OneAI designs one from what was
asked (ai.py), and approving the card makes it here, as Administrator, since
frappe makes DocTypes for its own managers alone.

What a workspace's record type may be, whoever asks:

- plain fields of the kinds a form is made of (`FIELDTYPES`): text, numbers,
  money, dates, ticks, choices, files, and links to a kind of record the
  administrator may open, or to another record type. Nothing that runs:
  no code, no HTML block, no button, no condition on another field;
- a name that is not taken, by frappe, an app, or another record type;
- belonging to one app: its users make and change records of it, its
  managers delete them, and it is listed in that app's rail under Your
  Records. One is everybody's.

Changing one adds fields, renames them and changes their choices; a field
already holding data is never dropped, only hidden. Deleting one deletes its
records, so it is refused while it has any.
"""

import json
import re

import frappe
from frappe import _

from onedesk.one import notify, roles
from onedesk.one_studio import extensions

RECORD_TYPE = "Record Type"
MODULE = "One Studio"

#: What a field of a workspace's record type may be.
FIELDTYPES = (
	"Data",
	"Small Text",
	"Text",
	"Text Editor",
	"Int",
	"Float",
	"Currency",
	"Percent",
	"Date",
	"Datetime",
	"Time",
	"Check",
	"Select",
	"Link",
	"Attach",
	"Attach Image",
	"Phone",
	"Rating",
	"Duration",
	"Section Break",
	"Column Break",
)

#: What a field may say of itself, beside its label and kind.
FIELD_KEYS = ("label", "fieldtype", "options", "reqd", "in_list_view", "description")

#: A name a person can read: words, spaces, and nothing frappe would refuse.
NAME = re.compile(r"^[A-Za-z][A-Za-z0-9 ]{2,60}$")

#: The most fields one may have.
MOST_FIELDS = 60


class Refused(Exception):
	"""Not what a workspace's record type may be. Its text says why."""


def _apps() -> dict:
	"""The apps a record type may belong to, as their rail's module, and the
	roles that use and manage each."""
	from onedesk.one import reports
	from onedesk.one.settings import APPS

	held = {one["label"]: one["module"] for one in reports.places()}
	out = {"One": {"module": held.get("One"), "users": ("Desk User",), "managers": ()}}
	for label, _code, users, managers in APPS:
		if label in held:
			out[label] = {"module": held[label], "users": users, "managers": managers}
	return out


def check(title: str, app: str, fields: list, record_type: str | None = None) -> list[dict]:
	"""Refuse what a workspace's record type may not be; return its fields as
	frappe keeps them."""
	roles.require()
	if app not in _apps():
		raise Refused(_("{0} is not an app a collection can belong to.").format(app))
	if not record_type:
		if not NAME.match(title or ""):
			raise Refused(_("A collection's name is 3 to 60 letters, numbers and spaces."))
		if frappe.db.exists("DocType", title):
			raise Refused(_("{0} is already taken. Choose another name.").format(title))
	if not fields:
		raise Refused(_("A collection needs at least one field."))
	if len(fields) > MOST_FIELDS:
		raise Refused(_("A collection has at most {0} fields.").format(MOST_FIELDS))
	from onedesk.one import audit

	kinds = set(audit.kinds()) | set(frappe.get_all(RECORD_TYPE, pluck="record_doctype"))
	out, seen = [], set()
	for one in fields:
		if not isinstance(one, dict) or set(one) - set(FIELD_KEYS):
			raise Refused(
				_(
					"A field says only its label, kind, choices, whether it is required and whether it is in the list."
				)
			)
		fieldtype = one.get("fieldtype")
		if fieldtype not in FIELDTYPES:
			raise Refused(_("A collection can't have a {0} field.").format(fieldtype))
		label = (one.get("label") or "").strip()
		if not label and fieldtype not in ("Section Break", "Column Break"):
			raise Refused(_("Every field needs a label."))
		fieldname = frappe.scrub(label) if label else f"{frappe.scrub(fieldtype)}_{len(out)}"
		if fieldname in seen or fieldname in frappe.model.default_fields:
			raise Refused(_("{0} is there twice, or is a name frappe keeps for itself.").format(label))
		seen.add(fieldname)
		options = (one.get("options") or "").strip() or None
		if fieldtype == "Link" and options not in kinds:
			raise Refused(
				_("{0} links to {1}, which is not a kind of record you may open.").format(label, options)
			)
		if fieldtype == "Select" and not options:
			raise Refused(_("{0} needs its choices, one a line.").format(label))
		if fieldtype not in ("Link", "Select", "Currency") and options:
			options = None
		out.append(
			{
				"fieldname": fieldname,
				"label": label or None,
				"fieldtype": fieldtype,
				"options": options,
				"reqd": int(bool(one.get("reqd"))),
				"in_list_view": int(bool(one.get("in_list_view"))),
				"description": (one.get("description") or "").strip()[:280] or None,
			}
		)
	return out


def _permissions(app: str) -> list[dict]:
	every = {"read": 1, "write": 1, "create": 1, "report": 1, "export": 1, "print": 1, "email": 1, "share": 1}
	spec = _apps()[app]
	rows = [{"role": roles.ADMINISTRATOR, **every, "delete": 1}]
	# frappe's own rule grants delete unless told not to.
	rows += [{"role": role, **every, "delete": 0} for role in spec["users"]]
	rows += [{"role": role, **every, "delete": 1} for role in spec["managers"]]
	return rows


def make(title: str, app: str, description: str, fields: list, asked: str) -> str:
	"""A new record type: frappe's DocType, ours beside it, and a place in its
	app's rail."""
	kept = check(title, app, fields)
	title_field = next((one["fieldname"] for one in kept if one["fieldtype"] == "Data"), None)
	with extensions._as_administrator():
		doctype = frappe.get_doc(
			{
				"doctype": "DocType",
				"name": title,
				"module": MODULE,
				"custom": 1,
				"autoname": "hash",
				"title_field": title_field,
				"show_title_field_in_link": int(bool(title_field)),
				"search_fields": title_field,
				"track_changes": 1,
				"sort_field": "modified",
				"sort_order": "DESC",
				"description": description,
				"fields": kept,
				"permissions": _permissions(app),
			}
		).insert(ignore_permissions=True)
	frappe.get_doc(
		{
			"doctype": RECORD_TYPE,
			"record_doctype": doctype.name,
			"app": app,
			"description": description,
			"asked": asked,
			"asked_by": frappe.session.user,
		}
	).insert(ignore_permissions=True)
	_place(doctype.name, app)
	notify.notify("Collection Added", roles.administrators(), **_told(doctype.name, app, description))
	return doctype.name


def change(record_type: str, app: str, description: str, fields: list, asked: str) -> str:
	"""A record type changed: its fields added, relabelled or given new
	choices, in the order given; one left out is hidden, never dropped."""
	ours = frappe.get_doc(RECORD_TYPE, record_type)
	ours.check_permission("read")
	kept = check(ours.record_doctype, app, fields, record_type=record_type)
	with extensions._as_administrator():
		doctype = frappe.get_doc("DocType", ours.record_doctype)
		had = {row.fieldname: row for row in doctype.fields}
		rows = []
		for one in kept:
			row = had.pop(one["fieldname"], None)
			rows.append(row.update({**one, "hidden": 0}) if row else one)
		for left in had.values():
			left.hidden = 1
			rows.append(left)
		doctype.set("fields", rows)
		doctype.description = description
		doctype.set("permissions", _permissions(app))
		doctype.save(ignore_permissions=True)
	if ours.app != app:
		from onedesk.one import reports

		reports._take("DocType", ours.record_doctype)
		_place(ours.record_doctype, app)
	ours.update({"app": app, "description": description, "asked": asked, "asked_by": frappe.session.user})
	ours.save(ignore_permissions=True)
	notify.notify(
		"Collection Changed", roles.administrators(), **_told(ours.record_doctype, app, description)
	)
	return ours.record_doctype


def _told(doctype: str, app: str, description: str | None, link: bool = True) -> dict:
	"""What the other administrators hear of a collection added, changed or
	deleted (notifications.py): it is in its app for everyone."""
	shown = [
		_(df.label)
		for df in frappe.get_meta(doctype).fields
		if df.label and not df.hidden and df.fieldtype not in ("Section Break", "Column Break", "Tab Break")
	]
	return {
		"link": f"/desk/{frappe.scrub(doctype).replace('_', '-')}" if link else None,
		"who": frappe.utils.get_fullname(frappe.session.user),
		"collection": _(doctype),
		"app": _(app),
		# A sentence of its own before the fields, however it was written.
		"description": (description or "").strip().rstrip(".") + "." if (description or "").strip() else "",
		"fields": ", ".join(shown),
	}


def _place(doctype: str, app: str) -> None:
	from onedesk.one import reports

	module = _apps()[app]["module"]
	if module:
		reports._put("DocType", doctype, module, None)


def restored(ours) -> str:
	"""A collection put back from the Recycle Bin (one/recycle.py): its DocType
	from the bin too, where it went as Administrator's, and its place in its
	app. Its table was never dropped."""
	roles.require()
	if not frappe.db.exists("DocType", ours.record_doctype):
		gone = frappe.get_all(
			"Deleted Document",
			filters={"deleted_doctype": "DocType", "deleted_name": ours.record_doctype, "restored": 0},
			fields=["name", "data"],
			order_by="creation desc",
			limit=1,
		)
		if not gone:
			frappe.throw(_("{0} can't be restored.").format(ours.record_doctype))
		with extensions._as_administrator():
			doctype = frappe.get_doc(json.loads(gone[0].data))
			doctype.flags.from_restore = True
			doctype.insert(ignore_permissions=True)
		frappe.db.set_value(
			"Deleted Document", gone[0].name, {"restored": 1, "new_name": ours.record_doctype}
		)
	ours.flags.from_restore = True
	ours.insert(ignore_permissions=True)
	_place(ours.record_doctype, ours.app)
	return ours.name


def remove(doc, method=None) -> None:
	"""Record Type on_trash: its DocType goes with it, and out of the rail;
	refused while it has records."""
	if not frappe.db.exists("DocType", doc.record_doctype):
		return
	if frappe.db.count(doc.record_doctype):
		frappe.throw(
			_("{0} still has records. Delete them first.").format(
				doc.record_doctype
			)
		)
	from onedesk.one import reports

	notify.notify(
		"Collection Deleted",
		roles.administrators(),
		**_told(doc.record_doctype, doc.app, doc.description, link=False),
	)
	reports._take("DocType", doc.record_doctype)
	with extensions._as_administrator():
		frappe.delete_doc("DocType", doc.record_doctype, ignore_permissions=True, force=True)
