"""A person's User and their Employee say the same about them: name, gender,
birth date, mobile, photo and bio. Whichever is saved, the other follows, so
HR changing a mobile reaches OneMail's signature and a person renaming
themselves reaches payroll. ERPNext copies a few of these one way on its own
(Employee.update_user); this covers all of them, both ways.

AccountCenter's Profile saves both records itself (center._save_profile),
under the same flag, so neither save starts the other."""

import frappe
from frappe.utils import escape_html, strip_html_tags

# User field: Employee field.
PAIRS = {
	"first_name": "first_name",
	"middle_name": "middle_name",
	"last_name": "last_name",
	"gender": "gender",
	"birth_date": "date_of_birth",
	"mobile_no": "cell_number",
	"user_image": "image",
	"bio": "bio",
}

FLAG = "one_syncing_person"


def plain(html: str | None) -> str:
	"""The Employee's bio, a Text Editor, as the User's plain text. Pure but
	for frappe's tag stripping."""
	return strip_html_tags((html or "").replace("<br>", "\n").replace("</p>", "\n")).strip()


def rich(text: str | None) -> str:
	"""The User's plain bio as the Employee's Text Editor holds it. Pure."""
	return "".join(f"<p>{escape_html(line)}</p>" for line in (text or "").splitlines() if line.strip())


def to_employee(user, employee, fields) -> None:
	"""These User fields onto the Employee (unsaved), emptied too: only the
	ones that changed are passed, so an empty one is a person clearing it."""
	for mine in fields:
		theirs = PAIRS[mine]
		value = user.get(mine)
		if mine == "bio":
			if plain(employee.bio) != (value or "").strip():
				employee.bio = rich(value)
		elif (employee.get(theirs) or None) != (value or None):
			employee.set(theirs, value)


def to_user(employee, user, fields) -> None:
	"""These Employee fields onto the User (unsaved), by their User name."""
	for mine in fields:
		value = employee.get(PAIRS[mine])
		if mine == "bio":
			if (user.bio or "").strip() != plain(value):
				user.bio = plain(value)
		elif (user.get(mine) or None) != (value or None):
			user.set(mine, value)


def _changed(doc, fields: dict) -> list[str]:
	"""The User names of the pair fields this save changed."""
	before = doc.get_doc_before_save()
	if not before:
		return []
	return [mine for mine, field in fields.items() if before.get(field) != doc.get(field)]


def from_user(doc, method=None) -> None:
	"""User on_update."""
	changed = _changed(doc, {mine: mine for mine in PAIRS})
	if frappe.flags.get(FLAG) or not changed or not frappe.db.exists("DocType", "Employee"):
		return
	name = frappe.db.get_value("Employee", {"user_id": doc.name}, "name")
	if not name:
		return
	employee = frappe.get_doc("Employee", name)
	to_employee(doc, employee, changed)
	frappe.flags[FLAG] = True
	try:
		employee.flags.ignore_permissions = True
		employee.save()
	finally:
		frappe.flags[FLAG] = False


def from_employee(doc, method=None) -> None:
	"""Employee on_update."""
	changed = _changed(doc, PAIRS)
	if frappe.flags.get(FLAG) or not doc.user_id or not changed:
		return
	user = frappe.get_doc("User", doc.user_id)
	to_user(doc, user, changed)
	frappe.flags[FLAG] = True
	try:
		user.flags.ignore_permissions = True
		user.save()
	finally:
		frappe.flags[FLAG] = False
