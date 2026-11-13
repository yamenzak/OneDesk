"""What a site holds under an app's old name, moved to its new one, for a
module's rename patch (one_doc/patches/writer_is_doc.py is one). The app's
roles take the new names through frappe's own rename, merged into what a
migrate made first; Role and Notification Type `one_app` follow, and so do
the defaults whose key names the app (abilities settled, AccessCenter).
Safe to run twice."""

import frappe
from frappe.cache_manager import clear_defaults_cache
from frappe.model.rename_doc import rename_doc


def app_renamed(old: str, new: str, roles: dict[str, str]) -> None:
	"""Move `old` to `new` everywhere a site keeps the app's name, and each
	role in `roles` (old name to new) with it."""
	for was, now in roles.items():
		_role(was, now)
	for doctype in ("Role", "Notification Type"):
		if frappe.db.has_column(doctype, "one_app"):
			frappe.db.set_value(doctype, {"one_app": old}, "one_app", new, update_modified=False)
	_defaults(((old, new), (frappe.scrub(old), frappe.scrub(new))))
	frappe.clear_cache()


def _role(old: str, new: str) -> None:
	if frappe.db.exists("Role", old):
		rename_doc(
			"Role",
			old,
			new,
			force=True,
			merge=bool(frappe.db.exists("Role", new)),
			ignore_permissions=True,
			show_alert=False,
			rebuild_search=False,
			validate=False,
		)
	if frappe.db.exists("Role", new):
		frappe.db.set_value("Role", new, "role_name", new, update_modified=False)


def _defaults(keys: tuple[tuple[str, str], ...]) -> None:
	table = frappe.qb.DocType("DefaultValue")
	for old, new in keys:
		rows = frappe.qb.from_(table).select(table.name, table.parent, table.defkey).where(table.defkey.like(f"%{old}%")).run(as_dict=True)
		for row in rows:
			key = row.defkey.replace(old, new)
			if key == row.defkey:
				continue
			if frappe.db.exists("DefaultValue", {"parent": row.parent, "defkey": key}):
				frappe.db.delete("DefaultValue", {"name": row.name})
			else:
				frappe.db.set_value("DefaultValue", row.name, "defkey", key, update_modified=False)
	clear_defaults_cache()
