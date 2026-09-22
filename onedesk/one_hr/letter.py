"""An appointment letter carries the template it was told to use.

`introduction` and `terms` are both required on an Appointment Letter, and both
are filled by eleven lines of their form script when somebody picks a template:

    frm.doc.terms = [];
    ... frm.add_child("terms"); ...

Nothing on the server does it, so a letter made any other way — an import, an
API, the onboarding automation a workspace writes for itself — is refused with
`MandatoryError: [Appointment Letter, HR-APP-LETTER-00001]: terms`, naming a
table it cannot see how to fill.

It is the fourth instance of the same fault in this audit, after
`leave_balance`, the two benefit ceilings and the expense claim's cost centre,
and it gets the same answer: the template is read, on the server, before
validate, when the fields are empty. A letter that already carries terms keeps
them, because somebody edited them deliberately.
"""



def before_validate(doc, method=None) -> None:
	if not doc.appointment_letter_template:
		return
	if doc.introduction and doc.terms:
		return

	from hrms.hr.doctype.appointment_letter.appointment_letter import (
		get_appointment_letter_details,
	)

	# Their helper answers `[{introduction, closing_notes}, {"description": [rows]}]`
	# — the terms arrive under a key called `description`, which is also the name
	# of a field on each row. Read exactly as their own form script reads it.
	found = get_appointment_letter_details(doc.appointment_letter_template)
	if len(found) < 2:
		return

	intro, body = found[0], found[1]
	if not doc.introduction:
		doc.introduction = intro.get("introduction")
	if not doc.closing_notes:
		doc.closing_notes = intro.get("closing_notes")
	if doc.terms:
		return
	for row in body.get("description") or []:
		doc.append("terms", {"title": row.get("title"), "description": row.get("description")})
