"""Fields of a linked record, edited on this one and saved with it
(one/linked.py, docs/SHELL.md decision 5).

These fail when a linked section could edit what a person does not type (a
computed, fetched or read-only field, or layout), when the save stops being
one transaction checked against the loaded `modified` and the linked record's
own permission down to the field, and when the form stops sending what
changed however the record is saved.
"""

import ast
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

LINKED = tree.APP / "one" / "linked.py"
SOURCE = LINKED.read_text(encoding="utf-8")
HOOKS = (tree.APP / "hooks.py").read_text(encoding="utf-8")
JS = (tree.APP / "public" / "js" / "head.js").read_text(encoding="utf-8")


def _pure(*names):
	space = {"re": re, "_": lambda text: text}
	for node in ast.parse(SOURCE).body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") in (
			"PREFIX",
			"REFUSED",
			"TABLES",
		):
			exec(ast.unparse(node), space)
		if isinstance(node, ast.FunctionDef) and node.name in names:
			exec(ast.unparse(node), space)
	return [space[name] for name in names]


class _Df(dict):
	def __getattr__(self, key):
		return self.get(key)


def test_a_linked_field_has_a_name_no_field_of_a_record_has():
	(fieldname,) = _pure("fieldname")
	assert fieldname("custodian", "cell_number") == "one_linked__custodian__cell_number"


def test_a_sections_fields_are_read_one_to_a_line_or_by_commas_once_each():
	(names,) = _pure("names")
	assert names("cell_number\npersonal_email") == ["cell_number", "personal_email"]
	assert names(" cell_number, personal_email ,cell_number ") == ["cell_number", "personal_email"]
	assert names("") == [] and names(None) == []


def test_only_what_a_person_types_is_edited_here():
	(refused,) = _pure("refused")
	# A table is the linked record's own, in frappe's grid; a field kept to
	# some people is shown by their permission levels, not refused.
	for df in (
		_Df(fieldtype="Data"),
		_Df(fieldtype="Date"),
		_Df(fieldtype="Table"),
		_Df(fieldtype="Currency", permlevel=1),
	):
		assert refused(df) is None, df
	for df in (
		_Df(fieldtype="Section Break"),
		_Df(fieldtype="Read Only"),
		_Df(fieldtype="Data", fetch_from="customer.customer_name"),
		_Df(fieldtype="Data", is_virtual=1),
		_Df(fieldtype="Data", read_only=1),
	):
		assert refused(df), df


def test_the_section_is_laid_out_as_the_linked_form_lays_its_fields():
	(placing,) = _pure("placing")
	source = [
		("contact_section", "Section Break"),
		("cell_number", "Data"),
		("column_break_1", "Column Break"),
		("personal_email", "Data"),
		("education_section", "Section Break"),
		("education", "Table"),
		("history_section", "Section Break"),
		("notes", "Small Text"),
	]
	assert placing(source, ["cell_number", "personal_email"]) == ["cell_number", "|", "personal_email"]
	assert placing(source, ["cell_number", "personal_email", "education"]) == [
		"cell_number",
		"|",
		"personal_email",
		"-",
		"education",
	]
	# Another section, or a column already passed, starts a section here.
	assert placing(source, ["personal_email", "cell_number"]) == ["personal_email", "-", "cell_number"]
	assert placing(source, ["notes", "cell_number"]) == ["notes", "-", "cell_number"]


def test_the_linked_record_is_saved_in_the_same_save_or_not_at_all():
	# In the record's own save, after it and before the request commits, on
	# a draft and on a submitted record's Update alike.
	assert '"onedesk.one.linked.save",' in HOOKS
	assert '"on_update_after_submit": "onedesk.one.linked.save"' in HOOKS
	body = SOURCE.split("def save(", 1)[1]
	assert 'linked.check_permission("write")' in body, "the linked record's own permission"
	assert (
		'cstr(linked.modified) != cstr(change.get("modified"))' in body and "TimestampMismatchError" in body
	)
	assert "set(values) - set(names(row.fields))" in body, "only the section's fields"
	assert 'change.get("name") != doc.get(link_field)' in body, "not a record just linked"
	assert 'has_permlevel_access_to(name, permission_type="write")' in body, "a field kept to some people"
	assert "as_rows(linked, name, value)" in body, "a table is set whole"
	assert '"on_submit": [' in HOOKS and HOOKS.count('"onedesk.one.linked.save"') >= 2
	assert "frappe.db.commit" not in SOURCE, "the request's transaction is the save's"


def test_the_form_draws_frappes_controls_and_says_what_changed_as_it_changes():
	assert 'bootinfo["one_linked"] = linked.for_boot(bootinfo)' in (tree.APP / "one" / "boot.py").read_text()
	assert "Layout.prototype.get_doctype_fields" in JS, "the section is part of the form's own layout"
	# Frappe runs no validate on Update and a grid edit fires none of ours, so
	# what changed is gathered where frappe saves, whatever the action.
	assert "frappe.ui.form.save = function (frm, ...rest)" in JS and "onedesk.head.collect(frm);" in JS
	assert 'trigger("validate")' not in JS and "validate(frm)" not in JS
	# The linked fields are in the record's own field copy, as a custom field is.
	assert "frappe.meta.make_docfield_copy_for = function" in JS
	assert "frm.doc.__one_linked = sent" in JS
	# As frappe does for the record itself: reload when clean, say so when not.
	assert "frm.debounced_reload_doc()" in JS and "doc_subscribe(doctype, name)" in JS
