"""An appointment letter carries the template it was told to use."""



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
