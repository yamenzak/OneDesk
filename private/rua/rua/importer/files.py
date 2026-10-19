"""The old app's files, each on what its record became, and so in OneCloud
under that record. Logos and photos stay public; everything else is
private, whatever the old app said: it kept passports and Emirates IDs
where anybody with the link could fetch them.

Signatures are not brought over, nor the old app's Google key, nor a file
no record held. OneIntake doesn't read what is brought over: two years of
history is not news, and somebody can ask it to read any one of them.
"""

import frappe

from rua.importer.people import DOCUMENT, EMPLOYEE, company_paper, kind

FILE = "File"
FACES = {"image", "custom_image"}
SKIPPED = {"signature", "service_account"}
KEEP = {
	"RUA Invoice": ("Sales Invoice", "Payment Request"),
	"RUA Payment": ("Payment Entry", "Purchase Invoice"),
	"RUA LPO": ("Purchase Order",),
	"RUA RFQ": ("Request for Quotation",),
	"RUA Quotation": ("Quotation",),
	"RUA Purchase Receipt": ("Purchase Receipt",),
	"RUA Employee": ("Employee",),
	"RUA Project": ("Project", "Opportunity"),
	"RUA Party": ("Customer", "Supplier"),
	"RUA Letter": ("Employee Letter",),
}
COVER = {"Customer": "image", "Supplier": "image", "Employee": "image", "Project": "one_cover"}


def run(run_):
	documents = {one["name"]: one for one in run_.docs(DOCUMENT)}
	records = {"RUA RFQ": {one["name"]: one for one in run_.docs("RUA RFQ")}}
	frappe.flags.one_intake_writing = True
	left = 0
	try:
		for count, old in enumerate(run_.source.files()):
			if old.get("is_folder") or not old.get("file_url"):
				continue
			if run_.made(FILE, old["name"], FILE):
				continue
			where = home(run_, old, documents, records)
			if not where:
				left += 1
				continue
			bring(run_, old, *where)
			if count % 50 == 0:
				frappe.db.commit()
	finally:
		frappe.flags.one_intake_writing = False
	if left:
		run_.note(
			"Left Out", None, None, f"{left} files no record held, signatures, or the old app's own settings"
		)


def home(run_, old, documents, records):
	"""Where an old file goes: (doctype, name, field to set or None, the
	Employee Document row it is the scan of or None)."""
	doctype, name, field = (
		old.get("attached_to_doctype"),
		old.get("attached_to_name"),
		old.get("attached_to_field"),
	)
	if not doctype or field in SKIPPED:
		return None
	if doctype == DOCUMENT:
		return paper(run_, documents.get(name))
	for target in KEEP.get(doctype, ()):
		made = run_.made(doctype, name, target)
		if made:
			return target, made, COVER.get(target) if field in FACES else None, None
	if doctype == "RUA RFQ":
		project = run_.made("RUA Project", (records["RUA RFQ"].get(name) or {}).get("project"), "Project")
		return ("Project", project, None, None) if project else None
	return None


def paper(run_, document):
	if not document:
		return None
	owner = document.get("for_docname")
	if document.get("source_doctype") == "RUA Project":
		project = run_.made("RUA Project", owner, "Project")
		return ("Project", project, None, None) if project else None
	if company_paper(document.get("document_name")):
		return "Company", run_.company, None, None
	employee = run_.made(EMPLOYEE, owner, "Employee")
	if not employee:
		return None
	row = (
		run_.made(DOCUMENT, document["name"], "Employee Document")
		if kind(document.get("document_name"))
		else None
	)
	return "Employee", employee, None, row


def bring(run_, old, doctype, name, field, row):
	content = run_.source.content(old["file_url"])
	if content is None:
		run_.note(
			"Left Out",
			doctype,
			name,
			f"{old.get('file_name') or old['file_url']}: the old site no longer has it",
		)
		return
	doc = frappe.get_doc(
		{
			"doctype": FILE,
			"file_name": old.get("file_name") or old["file_url"].rsplit("/", 1)[-1],
			"attached_to_doctype": doctype,
			"attached_to_name": name,
			"attached_to_field": field,
			"is_private": 0 if field else 1,
			"content": content,
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert()
	if field and not frappe.db.get_value(doctype, name, field):
		frappe.db.set_value(doctype, name, field, doc.file_url, update_modified=False)
	if row:
		frappe.db.set_value("Employee Document", row, "attachment", doc.file_url, update_modified=False)
	run_.remember(FILE, old["name"], FILE, doc.name)
