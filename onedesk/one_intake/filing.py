"""Filing: where a document goes once it is understood (docs/INTAKE.md §8, §13).

A document that belongs to a record is attached to it, so it is in the
record's Files tab, and File-Linked to the other records it belongs to. One
that belongs to no record goes to `{kind}/{year}` below the folder that was
switched on. It is named `2026-09-24 Stadtwerke Köln – Reminder Strom.pdf` in
the workspace's language and tagged with its kind, its year and OneAI. A file
somebody put in their own My Files is linked and tagged, never moved or
renamed. A message is linked to every record it is about, and junk that came
straight to a mailbox is moved out of the Inbox; junk that came through a
trusted channel (a scan, a forward) is set aside, never thrown away.

`plan` is pure: a reading and where it is, to a list of actions. `run` finds
out where it is, and hands each action to `act.apply`, the one door.
"""

import json
import re

import frappe
from frappe.utils import cint, getdate, today

from onedesk.one_intake.act import Action

#: A match this sure is the record a document belongs to (identity.CERTAIN).
CERTAIN = 0.9

#: Which party a document belongs to first: the person it is about, then who
#: sent it.
ROLES = ("Holder", "Patient", "Employee", "Sender", "Paid To", "Recipient", "Mentioned")

#: Sensitive documents are attached only to a person's own record; anywhere
#: else they are linked, since a link never grants read.
PERSONAL_RECORDS = ("Employee", "Job Applicant")

JUNK = ("Spam", "Phishing", "Advertising")
BULK = ("Newsletter", "Notification")

#: A name OneAI already gave, or one a person gave the same shape.
NAMED = re.compile(r"^\d{4}-\d{2}-\d{2} ")
UNSAFE = re.compile(r'[\\/:*?"<>|\n\r\t]+')
MOST_NAME = 120


# ------------------------------------------------------------------ pure


def records(parties: list[dict]) -> list[tuple[str, str]]:
	"""The records a document belongs to, the main one first. Pure."""
	sure = [one for one in parties if one.get("matched_doctype") and one.get("matched_name") and not one.get("ours") and (one.get("score") or 0) >= CERTAIN]
	sure.sort(key=lambda one: ROLES.index(one["role"]) if one.get("role") in ROLES else len(ROLES))
	out: list[tuple[str, str]] = []
	for one in sure:
		pair = (one["matched_doctype"], one["matched_name"])
		if pair not in out:
			out.append(pair)
	return out


def party_of(parties: list[dict]) -> str:
	"""Whom the name says a document is from or about. Pure."""
	for role in ROLES:
		for one in parties:
			if one.get("role") == role and not one.get("ours") and one.get("party_name"):
				return one["party_name"]
	return ""


def file_name(day, party: str, kind: str, title: str, extension: str) -> str:
	"""`2026-09-24 Stadtwerke Köln – Reminder Strom.pdf`. Pure."""
	title = title or ""
	for said in (party, kind):
		if said:
			title = re.sub(re.escape(said), " ", title, flags=re.IGNORECASE)
	title = " ".join(UNSAFE.sub(" ", title).replace("·", " ").split()).strip(" -–,.")
	head = " ".join(one for one in (str(day), UNSAFE.sub(" ", party or "").strip()) if one)
	tail = " ".join(one for one in (kind, title) if one)
	name = f"{head} – {tail}" if party and tail else " ".join(one for one in (head, tail) if one)
	name = " ".join(name.split())[:MOST_NAME].rstrip(" -–,.")
	return f"{name}.{extension}" if extension else name


def plan(reading: dict, where: dict) -> list[Action]:
	"""What filing does with one understood document. Pure.

	`reading` is the Reading as a dict, its parties included. `where` says
	where the document is: `file` (with `file_name`, `folder`, `own`,
	`attached`, `switched`, `extension`) or `message` (with `direct`,
	`in_inbox`, `junk`, `newsletters`), and `kind_label`, `today`, `tags`."""
	out: list[Action] = []
	verdict = reading.get("verdict") or ""
	kind = reading.get("kind") or ""
	parties = reading.get("parties") or []
	belongs = records(parties)
	# What the matter's earlier documents were filed with: a reminder that
	# names only an invoice number goes where the invoice went.
	belongs += [tuple(one) for one in where.get("matter_records") or [] if tuple(one) not in belongs]
	copy = bool(where.get("copy"))
	sure = {"sure": True, "confidence": 1}

	if where.get("message"):
		message = where["message"]
		if verdict in JUNK or verdict == "Newsletter":
			if where.get("direct") and where.get("in_inbox"):
				if verdict in ("Spam", "Phishing"):
					if where.get("junk"):
						out.append(Action("Move", "Communication", message, {"mail_folder": where["junk"]}, key="junk", **sure))
				else:
					out.append(Action("Move", "Communication", message, {"mail_folder": where["newsletters"]} if where.get("newsletters") else {"mail_folder_label": where.get("newsletters_label") or "Newsletters"}, key="newsletters", **sure))
			if verdict != "Newsletter":
				return out
		if verdict in JUNK:
			return out
		for doctype, name in belongs:
			out.append(Action("Link", doctype, name, {"message": message}, key=f"link|{doctype}|{name}", **sure))
		return out

	held = where.get("file")
	if not held:
		return out
	folder, own, attached = where.get("folder"), where.get("own"), where.get("attached")
	if verdict in JUNK:
		# From a trusted channel: set aside with the advertising, never deleted.
		if verdict in ("Spam", "Advertising") and not own and not attached and where.get("switched"):
			out.append(Action("Move", "File", held, {"under": where["switched"], "path": [where.get("advertising_label") or "Advertising"]}, key="advertising", **sure))
		return out

	name = where.get("file_name") or ""
	wanted = file_name(getdate(reading.get("issued_on") or where.get("today") or today()), party_of(parties), where.get("kind_label") or kind, reading.get("title") or "", where.get("extension") or "")
	rename = bool(kind) and not own and not NAMED.match(name) and wanted != name
	main = belongs[0] if belongs else None
	if main and reading.get("sensitivity") not in (None, "", "Ordinary") and main[0] not in PERSONAL_RECORDS:
		main = None
	# A file a person attached to a record stays there; it is only linked on.
	attach = bool(main) and not own and not copy and verdict != "Newsletter" and (not attached or attached[0] == "Communication") and attached != list(main)

	if attach:
		values = {"file": held}
		if attached and rename:
			values["file_name"] = wanted
		out.append(Action("Attach", main[0], main[1], values, key=f"attach|{main[0]}|{main[1]}", **sure))
	for doctype, record in belongs:
		if (attach and (doctype, record) == main) or [doctype, record] == attached:
			continue
		out.append(Action("Link", doctype, record, {"file": held, "reading": reading.get("name")}, key=f"link|{doctype}|{record}", **sure))
	if rename and not attached:
		out.append(Action("Rename", "File", held, {"file_name": wanted}, key="name", **sure))
	if not attach and not own and not copy and not attached and where.get("switched") and kind and verdict != "Newsletter" and where.get("file_away", 1):
		year = str(getdate(reading.get("issued_on") or where.get("today") or today()).year)
		out.append(Action("Move", "File", held, {"under": where["switched"], "path": [where.get("kind_label") or kind, year]}, key="file away", **sure))
	tags = [one for one in where.get("tags") or [] if one]
	if tags and kind:
		out.append(Action("Tag", "File", held, {"tags": tags}, key="tags", **sure))
	return out


# ------------------------------------------------------------------ on the site


def run(name: str) -> None:
	"""File one understood document, on behalf of whoever switched it on."""
	from onedesk.one_intake import act

	reading = frappe.get_doc("Reading", name)
	if not reading.on_behalf_of or cint(reading.history) or reading.state != "Understood":
		return
	if frappe.db.exists("Reading", {"part_of": name}):
		return
	held = _part_file(reading) if reading.part_of else None
	where = where_of(reading, held)
	if where is None:
		return
	said = reading.as_dict()
	said["parties"] = [one.as_dict() for one in reading.parties]
	for action in plan(said, where):
		action.key = f"{reading.key[:90]}|{action.key}"
		act.apply(action, reading)
	frappe.db.commit()
	_tell(reading)


def where_of(reading, held: str | None = None) -> dict | None:
	from frappe import _

	from onedesk.one_intake import switches

	language = frappe.db.get_single_value("System Settings", "language") or "en"
	kind_label = _(reading.kind, lang=language) if reading.kind else ""
	from onedesk.one_intake import matters

	where = {
		"matter_records": matters.records_of(reading.matter) if reading.matter and reading.matter != reading.name else [],
		"copy": bool(reading.copy_of),
		"today": today(),
		"kind_label": kind_label,
		"advertising_label": _("Advertising", lang=language),
		"newsletters_label": _("Newsletters", lang=language),
		"file_away": not cint(frappe.db.get_single_value("Intake Settings", "keep_in_place")),
	}
	if reading.source_doctype == "Communication" and not reading.part_of:
		comm = frappe.db.get_value("Communication", reading.source_name, ["name", "email_account", "one_folder", "sent_or_received"], as_dict=True)
		if not comm:
			return None
		from onedesk.one_mail import actions

		structured = json.loads(reading.structured or "{}")
		inbox = actions.folder_of(comm.email_account, "Inbox")
		where.update(
			{
				"message": comm.name,
				"direct": not structured.get("forwarded") and comm.sent_or_received == "Received",
				"in_inbox": bool(inbox) and comm.one_folder == inbox,
				"junk": frappe.db.get_value("Mail Folder", {"account": comm.email_account, "kind": "Junk"}, "name"),
				"newsletters": frappe.db.get_value("Mail Folder", {"account": comm.email_account, "label": where["newsletters_label"]}, "name"),
			}
		)
		return where
	held = held or (reading.source_name if reading.source_doctype == "File" and not reading.part_of else None)
	if not held:
		return None
	doc = frappe.db.get_value("File", held, ["name", "file_name", "folder", "attached_to_doctype", "attached_to_name", "is_folder"], as_dict=True)
	if not doc or doc.is_folder:
		return None
	switched = switches.of_folder(doc.folder)[0] if not doc.attached_to_doctype else None
	name, _dot, extension = (doc.file_name or "").rpartition(".")
	where.update(
		{
			"file": doc.name,
			"file_name": name or doc.file_name,
			"extension": extension.lower() if name else "",
			"folder": doc.folder,
			"own": _own(doc.folder),
			"attached": [doc.attached_to_doctype, doc.attached_to_name] if doc.attached_to_doctype and doc.attached_to_name else None,
			"switched": switched,
			"tags": [kind_label, str(getdate(reading.issued_on or today()).year), "OneAI"] if reading.kind else [],
		}
	)
	return where


def _own(folder: str | None) -> bool:
	"""Whether a folder is inside somebody's My Files."""
	from onedesk.one_storage import namespace as ns

	return any(frappe.db.get_value("File", at, "one_home_of") for at in ns.chain(folder)) if folder else False


def _part_file(reading) -> str | None:
	"""One letter of a batch scan, as a file of its own in the same place as
	the batch. The batch is kept as it came."""
	from onedesk.one_intake import act

	held = frappe.db.get_value("File", {"one_reading": reading.name}, "name")
	if held:
		return held
	parent = frappe.get_doc("Reading", reading.part_of)
	if parent.source_doctype != "File" or "#" not in (reading.key or ""):
		return None
	pages = _pages(reading.key.rsplit("#", 1)[1])
	source = frappe.db.get_value("File", parent.source_name, ["name", "file_name", "folder", "attached_to_doctype", "attached_to_name", "is_private"], as_dict=True)
	if not pages or not source or not (source.file_name or "").lower().endswith(".pdf"):
		return None
	done = act.apply(
		Action(
			"Create",
			"File",
			values={"source": source.name, "pages": pages, "reading": reading.name},
			key=f"{reading.key[:90]}|cut",
			flow="onedesk.one_intake.filing.cut",
			sure=True,
		),
		reading,
	)
	return frappe.db.get_value("Intake Action", done, "target_name") if done else None


def _pages(said: str) -> list[int]:
	first, _dash, last = said.partition("-")
	try:
		return list(range(int(first) - 1, int(last or first)))
	except ValueError:
		return []


def cut(values: dict):
	"""The flow that makes one letter's file out of a batch scan's pages."""
	from onedesk.one_intake.readers import pdf

	source = frappe.get_doc("File", values["source"])
	content = pdf.cut(source.get_content(), values["pages"])
	stem = source.file_name.rsplit(".", 1)[0]
	doc = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"{stem} {values['pages'][0] + 1}-{values['pages'][-1] + 1}.pdf",
			"folder": source.folder,
			"attached_to_doctype": source.attached_to_doctype,
			"attached_to_name": source.attached_to_name,
			"is_private": source.is_private,
			"content": content,
			"one_reading": values["reading"],
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc


def _tell(reading) -> None:
	"""Phishing is said at once to the person OneAI acts for, and a phishing
	file to whoever put it there."""
	from onedesk.one import notify

	# What waits for a person is said once the auditor has had its say
	# (inbox.tell), not here, before the rest is even made.
	if reading.verdict != "Phishing":
		return
	people = {reading.on_behalf_of}
	if reading.source_doctype == "File":
		people.add(frappe.db.get_value("File", reading.source_name, "owner"))
	# Once per person and document.
	notify.notify(
		"Phishing",
		list(people),
		record=("Reading", reading.name),
		sender=notify.ONEAI,
		dedupe_on=["document_type", "document_name"],
		title=reading.title or "",
	)


def forget(doc, method=None) -> None:
	"""on_trash: a file or a record that goes takes its File Links with it."""
	if doc.doctype == "File":
		frappe.db.delete("File Link", {"file": doc.name})
	elif doc.doctype not in ("File Link", "Intake Action", "AI Touch"):
		frappe.db.delete("File Link", {"for_doctype": doc.doctype, "for_name": doc.name})
