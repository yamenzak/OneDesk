"""The Intake panel: what OneAI read in a file or a message, beside it.

Asked for by OneCloud's preview and OneMail's reading pane. It answers only
somebody who may open the file or the message itself, and a party is shown
as a link only to somebody who may open that record.
"""

import hashlib
import json

import frappe
from frappe import _, _lt

from onedesk.one_storage import namespace as ns

FACTS = ("number", "issued_on", "gross", "paid_how", "iban", "payment_reference", "valid_until", "document_type", "issuing_country")


@frappe.whitelist()
def for_file(name: str) -> dict | None:
	item = ns.row(name)
	if not item or item.get("is_folder") or not ns.may(item):
		frappe.throw(_("That is no longer here."), frappe.DoesNotExistError)
	key, own = frappe.db.get_value("File", name, ["content_hash", "one_reading"])
	held = own or (frappe.db.get_value("Reading", {"key": key}, "name") if key else None)
	return described(held) if held else None


@frappe.whitelist()
def for_message(name: str) -> dict | None:
	comm = frappe.get_doc("Communication", name)
	comm.check_permission("read")
	key = "mail-" + hashlib.md5((comm.message_id or comm.name).encode()).hexdigest()
	held = frappe.db.get_value("Reading", {"key": key}, "name")
	if not held:
		return None
	said = described(held)
	files = frappe.get_all(
		"File",
		filters={"attached_to_doctype": "Communication", "attached_to_name": name, "is_folder": 0},
		fields=["file_name", "content_hash"],
	)
	said["attachments"] = [
		{"file": one.file_name, **described(found, brief=True)}
		for one in files
		if one.content_hash and (found := frappe.db.get_value("Reading", {"key": one.content_hash}, "name"))
	]
	return said


def described(name: str, brief: bool = False) -> dict:
	"""A Reading as the panel draws it."""
	doc = frappe.get_doc("Reading", name)
	out = {
		"name": doc.name,
		"state": doc.state,
		"verdict": doc.verdict,
		"kind": doc.kind,
		"title": doc.title,
		"summary": doc.summary,
		"unsure": doc.unsure,
		"sensitivity": doc.sensitivity,
		"how": doc.how,
		"read_by_ai": bool(doc.model or doc.understood_on),
	}
	if brief:
		return out
	from onedesk.one_intake import explain, pay

	out["actions"] = actions_of(name)
	out["may_decide"] = _may_decide(doc)
	out["pay"] = pay.of(doc)
	out["explained"] = json.loads(doc.explained or "{}").get(f"explain:{frappe.local.lang or 'en'}")
	out["may_cancel"] = bool(doc.kind == "Contract" and explain._cancel_by(doc))
	out["quick"] = quick(doc, out["pay"])
	out["matter"] = matter_of(doc)
	meta = frappe.get_meta("Reading")
	# Paying says the IBAN and the reference once, beside its code.
	shown = [field for field in FACTS if not (out["pay"] and not out["pay"]["warn"] and field in ("iban", "payment_reference"))]
	out["facts"] = [
		{"label": _(meta.get_label(field)), "value": doc.get(field), "field": field, "currency": doc.currency}
		for field in shown
		if doc.get(field)
	]
	out["parties"] = [_party(row) for row in doc.parties]
	out["dates"] = [{"date": row.date, "what": _(row.what), "about": row.about, "found": row.found} for row in doc.dates]
	out["asks"] = [{"what": _(row.what), "detail": row.detail, "by": row.by_date} for row in doc.asks]
	out["dropped"] = [line for line in (doc.dropped or "").splitlines() if line]
	out["parts"] = [
		{"part": part.part, **described(part.name, brief=True)}
		for part in frappe.get_all("Reading", filters={"part_of": name}, fields=["name", "part"], order_by="creation")
	]
	return out


#: A reference's kind, as the line that shows it is called.
REFERENCE = {
	"Invoice": _lt("Invoice Number"),
	"Order": _lt("Order Number"),
	"Customer": _lt("Customer Number"),
	"Contract": _lt("Contract Number"),
	"Case": _lt("Case Number"),
	"Tax": _lt("Tax Reference"),
	"Policy": _lt("Policy Number"),
	"Other": _lt("Reference"),
}

#: Who a document is from, in the order worth looking for.
FROM = ("Sender", "Paid To", "Holder", "Patient", "Employee")


def quick(doc, pay: dict | None) -> list[dict]:
	"""The facts a person looks for first, for the short panel beside a file
	or above a message: who it is from and their tax numbers, its numbers,
	its dates and amounts, and what it asks. The rest is under Details."""
	out = []

	def add(label, value, kind: str = "text"):
		if value not in (None, "", 0):
			out.append({"label": str(label), "value": value, "type": kind, "currency": doc.currency})

	sender = next((row for role in FROM for row in doc.parties if row.role == role and not row.ours), None)
	if sender:
		add(_("From"), sender.party_name or sender.email)
		add(_("VAT ID"), sender.vat_id)
		add(_("Tax Number"), sender.tax_number)
		add(_("Register Number"), sender.register)
		add(_("Document Number"), sender.document_number)
	add(_("Number"), doc.number)
	for row in doc.refs[:3]:
		if row.value != doc.number:
			add(REFERENCE.get(row.kind) or _("Reference"), row.value)
	add(_("Issued On"), doc.issued_on, "date")
	if doc.kind in ("Invoice", "Receipt", "Credit Note", "Reminder") or doc.gross:
		add(_("Net"), doc.net if doc.tax else None, "currency")
		add(_("Tax"), doc.tax, "currency")
		add(_("Total"), doc.gross, "currency")
	add(_("Paid How"), _(doc.paid_how) if doc.paid_how and doc.paid_how != "Transfer" else None)
	for row in doc.dates:
		if row.what in ("Due", "Deadline", "Appointment") and row.date:
			add(_(row.what), row.date, "date")
			break
	add(_("Document Type"), _(doc.document_type) if doc.document_type else None)
	add(_("Valid Until"), doc.valid_until, "date")
	add(_("Notice Period"), doc.notice_period)
	if not (pay and pay.get("code")):
		add(_("Payment Reference"), doc.payment_reference)
	asked = [row for row in doc.asks if not row.promise][:2]
	for row in asked:
		by = _("by {0}").format(frappe.format(row.by_date, "Date")) if row.by_date else ""
		add(_("Asks"), " · ".join(filter(None, [_(row.what), row.detail, by])))
	return out


def _party(row) -> dict:
	said = {"role": _(row.role), "name": row.party_name or row.email, "ours": row.ours, "score": row.score}
	if row.matched_doctype and row.matched_name and frappe.has_permission(row.matched_doctype, "read", row.matched_name):
		said["record"] = [row.matched_doctype, row.matched_name]
	return said


# ------------------------------------------------------------------ what OneAI did


def actions_of(reading: str) -> list[dict]:
	"""What OneAI did or proposes with a document and its parts, as the
	reader may know it: a record they may not open is named by its type only."""
	names = [reading, *frappe.get_all("Reading", filters={"part_of": reading}, pluck="name")]
	rows = frappe.get_all(
		"Intake Action",
		filters={"reading": ["in", names], "level": ["in", ("Done", "Proposed", "Refused")]},
		fields=["name", "kind", "level", "target_doctype", "target_name", "why", "after", "before", "audit", "audit_why", "checked_by"],
		order_by="creation asc",
	)
	from onedesk.one_hr.hiring import AUTHOR

	out = []
	for row in rows:
		if row.kind == "Create" and row.target_doctype == "File" and row.level == "Done":
			continue
		said = said_of(row)
		if said:
			out.append(
				{
					"name": row.name,
					"level": row.level,
					"said": said,
					"change": change_of(row),
					"why": row.why,
					"record": _record(row),
					"audit": row.audit,
					"audit_why": row.audit_why,
					# Applied by the auditor rather than by a person or at once.
					"by_auditor": row.checked_by == AUTHOR,
				}
			)
	return out


def said_of(row) -> str:
	after = json.loads(row.after or "{}")
	record = f"{_(row.target_doctype)} {row.target_name or ''}".strip()
	if row.kind == "Create":
		return _("Make {0}").format(_(row.target_doctype)) if row.level == "Proposed" else _("Made {0}").format(record)
	if row.kind == "Update":
		if row.level == "Proposed":
			return _("Change {0}").format(record) if change_of(row) else _("Fill in {0}").format(record)
		return _("Changed {0}").format(record) if change_of(row) else _("Filled in {0}").format(record)
	if row.kind == "Add":
		return _("Add to {0}").format(record) if row.level == "Proposed" else _("Added to {0}").format(record)
	if row.kind == "Link":
		return _("Linked to {0}").format(record)
	if row.kind == "Attach":
		return _("Filed with {0}").format(record)
	if row.kind == "Rename":
		return _("Named it {0}").format(after.get("file_name") or "")
	if row.kind == "Move":
		if row.target_doctype == "File":
			return _("Moved it to {0}").format(" / ".join(_folder_path(after.get("folder"))))
		return _("Moved it to {0}").format(frappe.db.get_value("Mail Folder", after.get("mail_folder"), "label") or "")
	if row.kind == "Tag":
		return _("Tagged it {0}").format(", ".join(after.get("tags") or [])) if after.get("tags") else ""
	if row.kind == "Comment":
		return _("Commented on {0}").format(record)
	return ""


def change_of(row) -> list[dict]:
	"""What a proposed change would write over, field by field."""
	if row.kind != "Update":
		return []
	before, after = json.loads(row.before or "{}"), json.loads(row.after or "{}")
	meta = frappe.get_meta(row.target_doctype)
	return [
		{"field": _(meta.get_label(key)), "from": before.get(key), "to": value}
		for key, value in after.items()
		if key != "name" and before.get(key) not in (None, "") and str(before.get(key)) != str(value)
	]


def _record(row) -> list | None:
	if row.target_doctype in ("File", "Communication") or not row.target_name:
		return None
	if frappe.db.exists(row.target_doctype, row.target_name) and frappe.has_permission(row.target_doctype, "read", row.target_name):
		return [row.target_doctype, row.target_name]
	return None


def _folder_path(folder: str | None) -> list[str]:
	from onedesk.one_storage import namespace as ns

	chain = ns.chain(folder)[:2] if folder else []
	return [frappe.db.get_value("File", at, "file_name") for at in reversed(chain)]


def matter_of(doc) -> dict | None:
	"""The matter a later document belongs to, and what it changes there."""
	if not doc.get("matter") or doc.matter == doc.name:
		return None
	head = frappe.db.get_value("Reading", doc.matter, ["name", "title", "kind", "number"], as_dict=True)
	if not head:
		return None
	return {
		"title": head.title or head.number or head.kind,
		"document": document_of(head.name),
		"change": _(doc.change) if doc.change else None,
		"copy": bool(doc.copy_of),
	}


def _may_decide(doc) -> bool:
	from onedesk.one.roles import administers

	return bool(doc.on_behalf_of) and (frappe.session.user == doc.on_behalf_of or administers())


def document_of(reading: str) -> dict | None:
	"""The document a record was made from, for its banner."""
	from onedesk.one_intake import search

	doc = frappe.db.get_value("Reading", reading, ["name", "title", "source_doctype", "source_name", "part_of"], as_dict=True)
	if not doc:
		return None
	own = frappe.db.get_value("File", {"one_reading": reading}, ["name", "file_name", "folder", "attached_to_doctype", "attached_to_name"], as_dict=True)
	if own:
		return {"label": own.file_name, "route": search._file_route(own)}
	if doc.source_doctype == "File":
		file = frappe.db.get_value("File", doc.source_name, ["name", "file_name", "folder", "attached_to_doctype", "attached_to_name"], as_dict=True)
		if file:
			if file.attached_to_doctype == "Communication":
				return _message(file.attached_to_name, file.file_name)
			return {"label": file.file_name, "route": search._file_route(file)}
	if doc.source_doctype == "Communication":
		return _message(doc.source_name, doc.title)
	return {"label": doc.title, "route": None}


def _message(name: str, label: str) -> dict:
	thread, account = frappe.db.get_value("Communication", name, ["one_thread", "email_account"]) or (None, None)
	return {"label": label, "route": f"/app/onemail?box={account}&thread={thread or name}"}
