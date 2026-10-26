"""The Recycle Bin: what was deleted, and putting it back.

Everybody puts back what they deleted, and whoever holds Everyone's
Deletions what anybody deleted of the kinds they may read, by frappe's own
restore. The page is the island `onedesk.recycle_bin`
(frontend/src/one/RecycleBin.vue) on the page `recycle-bin`.
"""

import json

import frappe
from frappe import _, _lt
from frappe.model.workflow import get_workflow_name
from frappe.permissions import get_doctypes_with_read

from onedesk.one import layer, roles
from onedesk.one_studio.customize import REFUSED_MODULES


def settle() -> None:
	"""The administrator's grant, and read for everybody, narrowed to their own
	deletions by `query` and `has_permission`."""
	_titles()


def _title(doctype: str, doc) -> str:
	"""What a deleted record is called in the bin: its title, a custom field's
	label (the list adds its form), or its name."""
	if doctype == "Custom Field":
		return doc.get("label") or doc.get("name") or ""
	meta = frappe.get_meta(doctype) if frappe.db.exists("DocType", doctype) else None
	field = meta.get_title_field() if meta else None
	return str((field and doc.get(field)) or doc.get("name") or "")[:140]


def titled(doc, method=None) -> None:
	"""on_trash: frappe writes the Deleted Document after every hook and with
	none of its own, so its title is set just before the transaction commits.
	The bin then lists a record by its title, not its ID."""
	if doc.doctype == "Deleted Document" or not frappe.get_meta("Deleted Document").has_field("one_title"):
		return
	title = _title(doc.doctype, doc)
	frappe.db.before_commit.add(
		lambda: frappe.db.set_value(
			"Deleted Document",
			{"deleted_doctype": doc.doctype, "deleted_name": doc.name, "one_title": ("is", "not set")},
			"one_title",
			title,
			update_modified=False,
		)
	)


def _titles() -> None:
	"""What was deleted before the bin kept titles, given one from what it kept."""
	if not frappe.get_meta("Deleted Document").has_field("one_title"):
		return
	for row in frappe.get_all(
		"Deleted Document",
		filters={"one_title": ("is", "not set")},
		fields=["name", "deleted_doctype", "deleted_name", "data"],
	):
		try:
			kept = json.loads(row.data or "{}")
		except ValueError:
			kept = {}
		title = _title(row.deleted_doctype, frappe._dict(kept)) or row.deleted_name
		frappe.db.set_value("Deleted Document", row.name, "one_title", title, update_modified=False)


def _trusted(user: str) -> bool:
	return user == "Administrator" or (user == frappe.session.user and not layer.held())


SYSTEM = ("Administrator", "Guest")

MACHINERY = ("Core", "Custom")

RESTORERS = {
	"Custom Field": "onedesk.one_studio.customize.restored",
	"Record Type": "onedesk.one_studio.record_types.restored",
}


MADE_BY_PEOPLE = ("Event", "Note", "ToDo")


def _machinery() -> list[str]:
	"""Every kind of record the bin leaves out: tables, frappe's machinery and
	the platform's own."""
	modules = [*MACHINERY, *REFUSED_MODULES]
	kept = [*RESTORERS, *MADE_BY_PEOPLE]
	return frappe.get_all(
		"DocType", filters={"module": ["in", modules], "name": ["not in", kept]}, pluck="name"
	) + frappe.get_all("DocType", filters={"istable": 1}, pluck="name")


def _kinds(user: str) -> list[str]:
	"""The kinds of record somebody who sees everyone's deletions sees: those
	they may read and that are records."""
	left_out = set(_machinery())
	return [one for one in get_doctypes_with_read() if one not in left_out] + list(RESTORERS)


def _everyone(user: str) -> bool:
	"""Whether somebody sees what anybody deleted: an administrator, or a role
	holding One's Everyone's Deletions (one/abilities.py)."""
	from onedesk.one import rights

	return rights.held("Deleted Document", "all_deletions", user)


def query(user: str | None = None) -> str | None:
	"""permission_query_conditions: one's own deletions, and, for whoever sees
	everyone's, the kinds they may read."""
	user = user or frappe.session.user
	if _trusted(user):
		return None
	left_out = ", ".join(frappe.db.escape(one) for one in set(_machinery())) or "''"
	own = (
		f"(`tabDeleted Document`.`owner` = {frappe.db.escape(user)}"
		f" and `tabDeleted Document`.`deleted_doctype` not in ({left_out}))"
	)
	if not _everyone(user):
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
	if ptype == "delete" and not roles.administers(user):
		return False
	if doc.owner == user and doc.deleted_doctype not in _machinery():
		return True
	return _everyone(user) and doc.owner not in SYSTEM and doc.deleted_doctype in _kinds(user)


PAGE = 50
KINDS_SHOWN = {"Record Type": _lt("Custom Collection")}


def _named(row) -> str:
	"""What a deleted record is called in the bin: a custom field says which
	kind of record it was on."""
	title = row.one_title or row.deleted_name
	if row.deleted_doctype == "Custom Field" and "-" in (row.deleted_name or ""):
		return _("{0} on {1}").format(title, _(row.deleted_name.rsplit("-", 1)[0]))
	return title


@frappe.whitelist(methods=["GET"])
@frappe.read_only()
def read(
	whose: str = "mine",
	state: str = "deleted",
	kind: str | None = None,
	search: str | None = None,
	start: int = 0,
) -> dict:
	"""The bin for the island (`onedesk.recycle_bin`): what the reader may see,
	newest first, a page at a time, with how many are deleted and put back
	and the kinds there are. `whose` is "mine", or "everyone" for whoever sees
	everybody's deletions."""
	user = frappe.session.user
	everyone = _everyone(user)
	filters = {}
	if whose != "everyone" or not everyone:
		filters["owner"] = user
	if kind:
		filters["deleted_doctype"] = kind
	or_filters = (
		{"one_title": ["like", f"%{search}%"], "deleted_name": ["like", f"%{search}%"]} if search else None
	)

	def counted(restored: int) -> int:
		return len(
			frappe.get_list(
				"Deleted Document",
				filters={**filters, "restored": restored},
				or_filters=or_filters,
				pluck="name",
				limit=10000,
			)
		)

	rows = frappe.get_list(
		"Deleted Document",
		filters={**filters, "restored": 1 if state == "restored" else 0},
		or_filters=or_filters,
		fields=[
			"name",
			"deleted_doctype",
			"deleted_name",
			"one_title",
			"owner",
			"creation",
			"modified",
			"new_name",
		],
		order_by="creation desc",
		start=int(start or 0),
		limit=PAGE + 1,
	)
	kinds = frappe.get_list(
		"Deleted Document",
		filters={key: value for key, value in filters.items() if key != "deleted_doctype"},
		fields=["deleted_doctype", {"COUNT": "*", "as": "count"}],
		group_by="deleted_doctype",
		limit=200,
	)
	kinds.sort(key=lambda one: -one.count)
	label = lambda doctype: str(KINDS_SHOWN.get(doctype) or _(doctype))  # noqa: E731
	return {
		"rows": [
			{
				"name": one.name,
				"title": _named(one),
				"doctype": one.deleted_doctype,
				"kind": label(one.deleted_doctype),
				"by": frappe.utils.get_fullname(one.owner),
				"mine": one.owner == user,
				"on": str(one.creation),
				"back_on": str(one.modified) if state == "restored" else None,
				"new_name": one.new_name,
			}
			for one in rows[:PAGE]
		],
		"more": len(rows) > PAGE,
		"counts": {"deleted": counted(0), "restored": counted(1)},
		"kinds": [
			{"doctype": one.deleted_doctype, "label": label(one.deleted_doctype), "count": one.count}
			for one in kinds
		],
		"everyone": everyone,
		"deletes": roles.administers(user),
	}


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
		deleted.modified = frappe.utils.now()
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
	doc.flags.name_set = not frappe.db.exists(doc.doctype, doc.name)
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
	deleted.modified = frappe.utils.now()
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
