"""The Recycle Bin (one/recycle.py): everybody sees their own deletions, an
administrator also what others deleted of what they may read, never the
system's cleanups or frappe's machinery; putting one back keeps frappe's own
checks. These read the code that says so."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

SOURCE = (tree.APP / "one" / "recycle.py").read_text()
HOOKS = (tree.APP / "hooks.py").read_text()


def _body(name: str) -> str:
	return SOURCE.split(f"def {name}(", 1)[1].split("\ndef ", 1)[0]


def test_the_bin_is_hooked():
	assert '"Deleted Document": "onedesk.one.recycle.query"' in HOOKS
	assert '"Deleted Document": "onedesk.one.recycle.has_permission"' in HOOKS
	assert '"onedesk.one.recycle.settle"' in HOOKS


def test_who_sees_what():
	query = _body("query")
	assert "`tabDeleted Document`.`owner` = " in query and "not in ({left_out})" in query
	assert "roles.administers(user)" in query and "not in ({system})" in query
	allowed = _body("has_permission")
	assert 'ptype == "delete" and not admin' in allowed
	assert "doc.owner not in SYSTEM" in allowed


def test_putting_back_keeps_frappes_checks():
	restore = _body("restore")
	assert 'frappe.has_permission("Deleted Document", "read", doc=deleted)' in restore
	assert 'frappe.has_permission(doc.doctype, "create")' in restore
	assert 'frappe.has_permission(doc.doctype, "read", doc=doc)' in restore
	assert "only_for" not in restore


def test_machinery_and_tables_stay_out():
	assert 'MACHINERY = ("Core", "Custom")' in SOURCE
	assert '"istable": 1' in _body("_machinery")


def test_a_custom_field_and_a_collection_come_back_whole():
	"""A custom field and a collection are frappe machinery an administrator
	still sees in the bin, and each comes back through its own restorer: the
	field into the Custom Fields list with its values, the collection with
	its DocType and its place in its app."""
	assert '"Custom Field": "onedesk.one.customize.restored"' in SOURCE
	assert '"Record Type": "onedesk.one_studio.record_types.restored"' in SOURCE
	assert '"name": ["not in", list(RESTORERS)]' in _body("_machinery")
	assert "frappe.get_attr(RESTORERS[doc.doctype])(doc)" in _body("restore")
	customize = (tree.APP / "one" / "customize.py").read_text().split("def restored(", 1)[1].split("\ndef ", 1)[0]
	assert "may(field.dt)" in customize and '_note(field.dt, "Custom Field", field.name)' in customize
	studio = (tree.APP / "one_studio" / "record_types.py").read_text().split("def restored(", 1)[1].split("\ndef ", 1)[0]
	assert "roles.require()" in studio and '"deleted_doctype": "DocType"' in studio
	assert "_place(ours.record_doctype, ours.app)" in studio
