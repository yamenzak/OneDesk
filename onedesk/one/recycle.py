"""The Recycle Bin: what was deleted, and putting it back. docs/DESK-COVERAGE.md, P2.

Every record frappe deletes is kept whole as a `Deleted Document`, and frappe
puts one back with its own `restore`. Both are its System Manager's, whom no
workspace has, so nobody here could see or undo a deletion. Now:

- everybody sees what they deleted themselves, and puts it back;
- a workspace administrator also sees what any person (or OneAI) deleted, of
  the kinds of record they may read, though not the system's own cleanups;
  puts it back; and may empty it for good;
- what is not a record somebody made is never shown: tables, frappe's own
  machinery (permission rows, property setters) and the platform's records.

Putting one back is frappe's own restore (below, from
frappe/core/doctype/deleted_document/deleted_document.py, MIT), with its
checks kept: whoever restores must be able to make and read that kind of
record. Frappe keeps a deleted record until somebody empties it; it is not
among the logs it clears on its own.
"""

import json

import frappe
from frappe import _
from frappe.model.workflow import get_workflow_name
from frappe.permissions import get_doctypes_with_read

from onedesk.one import layer, roles
from onedesk.one.customize import REFUSED_MODULES

GRANTS = {"Deleted Document": ("read", "delete")}


def settle() -> None:
	"""The administrator's grant, and read for everybody, narrowed to their own
	deletions by `query` and `has_permission`."""
	from frappe.permissions import add_permission, setup_custom_perms, update_permission_property

	roles.grant(GRANTS)
	where = {"parent": "Deleted Document", "role": "Desk User", "permlevel": 0, "if_owner": 0}
	if frappe.db.get_value("Custom DocPerm", where, "read"):
		return
	setup_custom_perms("Deleted Document")
	if not frappe.db.exists("Custom DocPerm", where):
		add_permission("Deleted Document", "Desk User", 0)
	update_permission_property("Deleted Document", "Desk User", 0, "read", 1, validate=False)


def _trusted(user: str) -> bool:
	return user == "Administrator" or (user == frappe.session.user and not layer.held())


#: Who deletes as the system rather than as a person: the scheduler, a patch, a
#: cleanup. What they delete is housekeeping, not anybody's to put back.
SYSTEM = ("Administrator", "Guest")

#: frappe's own machinery: what a customization or a permission writes, never a
#: record somebody made, and never in the bin.
MACHINERY = ("Core", "Custom")

#: What a workspace makes of frappe's machinery, which its administrators see
#: in the bin all the same, and what puts each back: a plain insert would
#: leave a field out of the Custom Fields list, or a collection without its
#: records. Each restorer checks who may and returns the name it came back as.
RESTORERS = {
	"Custom Field": "onedesk.one.customize.restored",
	"Record Type": "onedesk.one_studio.record_types.restored",
}


def _machinery() -> list[str]:
	"""Every kind of record the bin leaves out: tables, frappe's machinery and
	the platform's own."""
	modules = [*MACHINERY, *REFUSED_MODULES]
	return frappe.get_all(
		"DocType", filters={"module": ["in", modules], "name": ["not in", list(RESTORERS)]}, pluck="name"
	) + frappe.get_all("DocType", filters={"istable": 1}, pluck="name")


def _kinds(user: str) -> list[str]:
	"""The kinds of record an administrator sees deleted: those they may read
	and that are records."""
	left_out = set(_machinery())
	return [one for one in get_doctypes_with_read() if one not in left_out] + list(RESTORERS)


def query(user: str | None = None) -> str | None:
	"""permission_query_conditions: one's own deletions, and an administrator's
	readable kinds."""
	user = user or frappe.session.user
	if _trusted(user):
		return None
	left_out = ", ".join(frappe.db.escape(one) for one in set(_machinery())) or "''"
	own = (
		f"(`tabDeleted Document`.`owner` = {frappe.db.escape(user)}"
		f" and `tabDeleted Document`.`deleted_doctype` not in ({left_out}))"
	)
	if not roles.administers(user):
		return own
	kinds = ", ".join(frappe.db.escape(one) for one in _kinds(user)) or "''"
	system = ", ".join(frappe.db.escape(one) for one in SYSTEM)
	return (
		f"({own} or (`tabDeleted Document`.`deleted_doctype` in ({kinds})"
		f" and `tabDeleted Document`.`owner` not in ({system})))"
	)


def has_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
	"""has_permission: the same as `query`, for one deleted record. Only an
	administrator empties one for good."""
	user = user or frappe.session.user
	if _trusted(user):
		return True
	admin = roles.administers(user)
	if ptype == "delete" and not admin:
		return False
	if doc.owner == user and doc.deleted_doctype not in _machinery():
		return True
	return admin and doc.owner not in SYSTEM and doc.deleted_doctype in _kinds(user)


@frappe.whitelist(methods=["POST"])
def restore(name: str, alert: bool = True) -> str:
	"""A deleted record put back as it was, under its own name where it is
	free, by whoever may see it in the bin and make that kind of record."""
	deleted = frappe.get_doc("Deleted Document", name)
	if not frappe.has_permission("Deleted Document", "read", doc=deleted):
		frappe.throw(_("You cannot open {0}.").format(name), frappe.PermissionError)
	if deleted.restored:
		frappe.throw(
			_("{0} is back already.").format(deleted.deleted_name), exc=frappe.DocumentAlreadyRestored
		)

	doc = frappe.get_doc(json.loads(deleted.data))
	if doc.doctype in RESTORERS:
		name = frappe.get_attr(RESTORERS[doc.doctype])(doc)
		deleted.new_name = name
		deleted.restored = 1
		deleted.db_update()
		if alert:
			frappe.msgprint(_("{0} is back.").format(deleted.deleted_name), alert=True, indicator="green")
		return name
	if not frappe.has_permission(doc.doctype, "create"):
		frappe.throw(
			_("You cannot make a {0}, so you cannot put one back.").format(_(doc.doctype)),
			frappe.PermissionError,
		)
	if not frappe.has_permission(doc.doctype, "read", doc=doc):
		frappe.throw(_("You cannot open {0}.").format(deleted.deleted_name), frappe.PermissionError)

	was = {field: doc.get(field) for field in ("owner", "creation", "modified", "modified_by")}
	doc.flags.from_restore = True
	try:
		doc.insert()
	except frappe.DocstatusTransitionError:
		frappe.msgprint(_("It was cancelled, so it comes back as a draft."))
		doc.docstatus = 0
		flow = get_workflow_name(doc.doctype)
		state = flow and frappe.get_value("Workflow", flow, "workflow_state_field")
		if state and doc.get(state):
			doc.set(state, None)
		doc.insert()
	frappe.db.set_value(doc.doctype, doc.name, was, update_modified=False)
	doc.add_comment("Edit", _("restored {0} as {1}").format(deleted.deleted_name, doc.name))

	deleted.new_name = doc.name
	deleted.restored = 1
	deleted.db_update()
	if alert:
		frappe.msgprint(_("{0} is back.").format(doc.name), alert=True, indicator="green")
	return doc.name


@frappe.whitelist(methods=["POST"])
def bulk_restore(names: str | list) -> dict:
	"""Several put back at once; each that cannot be says why on its own."""
	said = {"restored": [], "already": [], "failed": []}
	for name in frappe.parse_json(names) or []:
		try:
			restore(name, alert=False)
			frappe.db.commit()
			said["restored"].append(name)
		except frappe.DocumentAlreadyRestored:
			frappe.clear_last_message()
			said["already"].append(name)
		except Exception:
			frappe.clear_last_message()
			frappe.db.rollback()
			said["failed"].append(name)
	return said
