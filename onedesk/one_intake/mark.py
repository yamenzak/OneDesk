"""The OneAI mark on a whole record: OneAI made this, and nobody has checked it.

It is an `AI Touch` row whose field is `*` (docs/INTAKE.md §4.2). The field
badge of `one_ai/touch.py` compares what OneAI wrote with what a field says
now; a record has nothing to compare, so its mark is a flag, and the flag is
taken down by a person doing something to the record: saving it, submitting
it, cancelling it, pressing Looks right, or merging another record into it.
Opening it does not, nor does ERPNext touching it with `db_set`, nor another
OneAI action, which writes with `frappe.flags.one_intake_writing` set.

The clearing hook runs on every save of every doctype, so it first asks a
cached set of the doctypes that carry any mark at all, which is a handful.
"""

import frappe
from frappe import _

from onedesk.one_hr.hiring import AUTHOR

#: The field an `AI Touch` row names when it marks the whole record.
WHOLE = "*"

#: The doctypes that carry a mark, cached; a save of anything else costs one
#: cache read.
CACHE = "one_intake_marked_doctypes"

#: How many marked names the list's filter hands the list view at most.
MOST_LISTED = 500


def marked_doctypes() -> set[str]:
	held = frappe.cache.get_value(CACHE)
	if held is None:
		held = frappe.get_all("AI Touch", filters={"fieldname": WHOLE}, pluck="for_doctype", distinct=True)
		frappe.cache.set_value(CACHE, held)
	return set(held)


def _changed() -> None:
	frappe.cache.delete_value(CACHE)


def mark(doctype: str, name: str, reading: str | None) -> None:
	"""Put the mark on a record OneAI just made."""
	if frappe.db.exists("AI Touch", {"for_doctype": doctype, "record": name, "fieldname": WHOLE}):
		return
	row = frappe.new_doc("AI Touch")
	row.update({"for_doctype": doctype, "record": name, "fieldname": WHOLE, "value": reading or "", "touched_by": AUTHOR})
	row.insert(ignore_permissions=True)
	if doctype not in marked_doctypes():
		_changed()


def reading_of(doctype: str, name: str) -> str | None:
	"""The reading a marked record was made from, or None when it carries no mark."""
	held = frappe.db.get_value("AI Touch", {"for_doctype": doctype, "record": name, "fieldname": WHOLE}, "value")
	return held if held is not None else None


def is_marked(doctype: str, name: str) -> bool:
	return bool(frappe.db.exists("AI Touch", {"for_doctype": doctype, "record": name, "fieldname": WHOLE}))


def clear(doctype: str, name: str, by: str | None = None) -> bool:
	"""Take the mark down, saying who checked it. True when there was one."""
	if not is_marked(doctype, name):
		return False
	frappe.db.delete("AI Touch", {"for_doctype": doctype, "record": name, "fieldname": WHOLE})
	frappe.db.set_value(
		"Intake Action",
		{"target_doctype": doctype, "target_name": name, "kind": "Create", "level": "Done"},
		"checked_by",
		by or frappe.session.user,
		update_modified=False,
	)
	return True


# ------------------------------------------------------------------ hooks


def _by_a_person() -> bool:
	flags = frappe.flags
	if flags.one_intake_writing or flags.in_import or flags.in_migrate or flags.in_install or flags.in_patch:
		return False
	return frappe.session.user not in (AUTHOR, "Guest")


def looked_at(doc, method=None) -> None:
	"""on_update, on_submit, on_cancel: a person did something to a marked record."""
	if doc.doctype == "AI Touch" or doc.doctype not in marked_doctypes() or not _by_a_person():
		return
	clear(doc.doctype, doc.name)


def before_rename(doc, method=None, old=None, new=None, merge=False) -> None:
	"""Whether the record kept in a merge carried the mark before it."""
	if merge and doc.doctype in marked_doctypes():
		frappe.flags.one_intake_kept_marked = is_marked(doc.doctype, new)


def after_rename(doc, method=None, old=None, new=None, merge=False) -> None:
	"""A merge moves the old record's rows onto the kept one, its mark with
	them. A person merging clears it; OneAI folding keeps it only where the
	kept record had one of its own."""
	if not merge or doc.doctype not in marked_doctypes():
		return
	kept = frappe.flags.pop("one_intake_kept_marked", False)
	rows = frappe.get_all("AI Touch", filters={"for_doctype": doc.doctype, "record": new, "fieldname": WHOLE}, pluck="name")
	if _by_a_person() or not kept:
		for row in rows:
			frappe.delete_doc("AI Touch", row, ignore_permissions=True, force=True)
	else:
		for row in rows[1:]:
			frappe.delete_doc("AI Touch", row, ignore_permissions=True, force=True)


def onload(doc, method=None) -> None:
	"""The form's banner: what made this, from which document."""
	if doc.doctype not in marked_doctypes() or doc.is_new():
		return
	reading = reading_of(doc.doctype, doc.name)
	if reading is None:
		return
	from onedesk.one_intake import panel

	doc.set_onload("one_intake_mark", {"reading": reading, "document": panel.document_of(reading), "action": _action_of(doc.doctype, doc.name)})


def _action_of(doctype: str, name: str) -> str | None:
	return frappe.db.get_value(
		"Intake Action", {"target_doctype": doctype, "target_name": name, "kind": "Create", "level": "Done"}, "name"
	)


# ------------------------------------------------------------------ asked by the desk


@frappe.whitelist()
def unchecked(doctype: str, names=None) -> dict:
	"""Which of a list page's records carry the mark, and how many of those
	the reader may see there are in all."""
	if not frappe.has_permission(doctype, "read") or doctype not in marked_doctypes():
		return {"names": [], "total": 0, "all": []}
	names = frappe.parse_json(names) if isinstance(names, str) else names or []
	held = frappe.get_all("AI Touch", filters={"for_doctype": doctype, "fieldname": WHOLE}, pluck="record")
	visible = frappe.get_list(doctype, filters={"name": ["in", held]}, pluck="name", limit_page_length=MOST_LISTED) if held else []
	shown = set(names)
	return {"names": [name for name in visible if name in shown], "total": len(visible), "all": visible}


@frappe.whitelist(methods=["POST"])
def looks_right(doctype: str, name: str) -> None:
	"""A person has checked a record OneAI made and says it is right."""
	frappe.get_doc(doctype, name).check_permission("write")
	if not clear(doctype, name):
		frappe.throw(_("Nobody needs to check {0} any more.").format(name))
