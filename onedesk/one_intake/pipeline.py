"""Stage 1 of Intake: every file and message that arrives becomes a Reading.

A file dropped in OneCloud, a file attached on a form and a message with its
attachments are each read in the background, once per content. What needs no
model (a text PDF, an e-invoice, a Word file, a bank statement) is read for
every file, so a workspace can search inside its documents whether or not it
uses OneAI. What needs a model (a scan, a photo, a recording) is read only
where somebody switched OneAI on, and is charged as OneAI credits.
"""

import hashlib
import json

import frappe
from frappe.utils import cint, now_datetime

from onedesk.one_intake import read, split, switches, vision

#: Frappe's own bookkeeping and our own pictures: files nobody sent.
SKIPPED = frozenset(
	(
		"Prepared Report", "Data Import", "Data Export", "Access Log", "Error Log", "Deleted Document",
		"Version", "Face", "AI Chat", "Interview Recording", "Letter Head", "Print Format", "User",
		"Website Settings", "Web Page", "Workspace", "Reading",
	)
)  # fmt: skip

#: What a Reading keeps of a very long text. The rest of a four-hundred-page
#: file is not what anybody searches for.
MOST_TEXT = 2_000_000

#: A picture smaller than this in a message is somebody's signature or logo.
SIGNATURE = 20 * 1024

#: How deep archives inside archives are opened.
DEEPEST = 3

#: How often a reading that failed for a passing reason is tried again.
TRIES = 5

DONE = ("Read", "Unreadable", "Needs a Password")


# ------------------------------------------------------------------ doors


def file_added(doc, method=None) -> None:
	"""File after_insert: read it in the background."""
	if not _readable_file(doc):
		return
	later("read_file", f"file:{doc.name}", name=doc.name)


def mail_arrived(made, arrival) -> None:
	"""Called by OneMail's Arrival once a message is filed."""
	if made.communication_medium != "Email":
		return
	later("read_mail", f"mail:{made.name}", name=made.name, history=int(not getattr(arrival, "fresh", True)))


def later(method: str, job: str, **kwargs) -> None:
	frappe.enqueue(
		f"onedesk.one_intake.pipeline.{method}",
		queue="long",
		job_id=f"one-intake-{job}",
		deduplicate=True,
		enqueue_after_commit=True,
		**kwargs,
	)


def _readable_file(doc) -> bool:
	if frappe.flags.one_intake_writing or doc.is_folder or not doc.file_url:
		return False
	if doc.attached_to_doctype in SKIPPED or doc.attached_to_doctype == "Communication":
		return False
	return not doc.get("one_deleted")


# ------------------------------------------------------------------ files


def read_file(name: str, history: int = 0) -> str | None:
	"""A File, read. Returns the Reading's name, or None when there is
	nothing to read or nobody asked for a model to read it."""
	doc = frappe.db.get_value(
		"File",
		name,
		["name", "file_name", "file_url", "content_hash", "is_folder", "attached_to_doctype", "attached_to_name", "folder", "owner", "file_size"],
		as_dict=True,
	)
	if not doc or doc.is_folder:
		return None
	person = switches.of_file(doc)
	if doc.content_hash:
		held = _held(doc.content_hash)
		if held and held.state in DONE and not _waiting_parts(held.name):
			return held.name
	try:
		content = frappe.get_doc("File", name).get_content()
	except Exception:
		frappe.log_error(title=f"Intake could not open the file {name}")
		return None
	if isinstance(content, str):
		content = content.encode()
	key = doc.content_hash or hashlib.md5(content).hexdigest()
	said = read.read(doc.file_name, content)
	if said.needs in ("eyes", "ears") and not person:
		return None
	reading = _reading(key, doc.file_name, ("File", name), person, history)
	if reading.state in DONE:
		# Read before, but a file inside it is still waiting: only that is read.
		for inner in said.inner:
			_inner(reading, inner, person, 0)
		return reading.name
	_fill(reading, doc.file_name, content, said, person)
	return reading.name


def _waiting_parts(name: str) -> bool:
	return bool(frappe.db.exists("Reading", {"part_of": name, "state": ["in", ("Queued", "Waiting for Credits")]}))


def _held(key: str):
	return frappe.db.get_value("Reading", {"key": key}, ["name", "state"], as_dict=True)


def _reading(key: str, title: str, source: tuple, person: str | None, history: int, **more):
	"""The Reading for this content, made the first time it is seen. Two jobs
	reading the same content at once make one: the key is unique."""
	held = _held(key)
	if held:
		doc = frappe.get_doc("Reading", held.name)
		if person and not doc.on_behalf_of:
			doc.on_behalf_of = person
		return doc
	doc = frappe.get_doc(
		{
			"doctype": "Reading",
			"key": key,
			"title": (title or key)[:140],
			"source_doctype": source[0],
			"source_name": source[1],
			"on_behalf_of": person,
			"history": cint(history),
			"state": "Queued",
			**more,
		}
	)
	try:
		doc.insert(ignore_permissions=True)
	except frappe.DuplicateEntryError:
		frappe.db.rollback()
		return frappe.get_doc("Reading", _held(key).name)
	return doc


def _fill(reading, name: str, content: bytes, said: read.Text, person: str | None, depth: int = 0) -> None:
	"""Put what was read into the Reading, asking a model where the file needs
	one, and read its parts: each letter in a batch scan, each file in a zip."""
	ext = read.extension(name)
	try:
		if said.needs == "eyes":
			seen = vision.see(name, content, ext, _most_pages(), reading.name)
			said.pages, said.language = seen["pages"], said.language or seen["language"]
			said.text = "\n\n".join(seen["pages"]).strip()
			said.documents = split.documents(seen["pages"], seen["starts"]) if ext == "pdf" else []
			said.how, reading.model = said.how or "Scan", vision.PAGES
			said.needs = None
		elif said.needs == "ears":
			said.text, said.how, reading.model, said.needs = vision.hear(name, content, ext, reading.name), "Recording", vision.SOUND, None
	except Exception as raised:
		_failed(reading, raised)
		return
	if said.needs == "password":
		_set(reading, state="Needs a Password", how=said.how)
		return
	if said.needs == "nothing":
		_set(reading, state="Unreadable", how=said.how)
		return
	if said.text and not said.language:
		from onedesk.one_intake import language

		said.language = language.guess(said.text)
	_set(
		reading,
		state="Read",
		how=said.how,
		text=(said.text or "")[:MOST_TEXT],
		language=said.language,
		page_count=len(said.pages) or None,
		structured=json.dumps(said.structured, default=str) if said.structured else None,
		read_on=now_datetime(),
		error=None,
	)
	if len(said.documents) > 1:
		for pages in said.documents:
			_part(reading, f"{reading.key}#{pages[0] + 1}-{pages[-1] + 1}", _pages_label(pages), "\n\n".join(said.pages[index] for index in pages))
	if depth < DEEPEST:
		for inner in said.inner:
			_inner(reading, inner, person, depth)


def _part(parent, key: str, label: str, text: str) -> None:
	doc = _reading(key, f"{parent.title} · {label}", (parent.source_doctype, parent.source_name), parent.on_behalf_of, parent.history, part_of=parent.name, part=label)
	from onedesk.one_intake import language

	_set(doc, state="Read", how=parent.how, text=text[:MOST_TEXT], language=language.guess(text) or parent.language, read_on=now_datetime())


def _inner(parent, inner: dict, person: str | None, depth: int) -> None:
	content = inner.get("content") or b""
	if not content:
		return
	said = read.read(inner["name"], content)
	if said.needs in ("eyes", "ears") and not person:
		return
	doc = _reading(
		hashlib.md5(content).hexdigest(),
		inner["name"],
		(parent.source_doctype, parent.source_name),
		person,
		parent.history,
		part_of=parent.name,
		part=inner["name"][:140],
	)
	if doc.state not in DONE:
		_fill(doc, inner["name"], content, said, person, depth + 1)


def _pages_label(pages: list[int]) -> str:
	first, last = pages[0] + 1, pages[-1] + 1
	return frappe._("page {0}").format(first) if first == last else frappe._("pages {0}–{1}").format(first, last)


def _most_pages() -> int:
	return cint(frappe.db.get_single_value("Intake Settings", "most_pages")) or 60


# ------------------------------------------------------------------ mail


def read_mail(name: str, history: int = 0) -> str | None:
	"""A message, read: its words, whom it is really from when it is a
	forward, and each of its attachments as a Reading of its own."""
	from onedesk.one_intake.readers import mail

	comm = frappe.db.get_value(
		"Communication",
		name,
		["name", "subject", "content", "sender", "sender_full_name", "recipients", "cc", "communication_date", "sent_or_received", "message_id", "email_account", "communication_medium"],
		as_dict=True,
	)
	if not comm or comm.communication_medium != "Email":
		return None
	person = switches.of_mailbox(comm.email_account)
	key = "mail-" + hashlib.md5((comm.message_id or comm.name).encode()).hexdigest()
	reading = _reading(key, comm.subject or "(no subject)", ("Communication", name), person, history, message_id=comm.message_id)
	attachments = [
		read_file(one.name, history) if _worth_reading(one, comm.content) else None
		for one in frappe.get_all(
			"File",
			filters={"attached_to_doctype": "Communication", "attached_to_name": name, "is_folder": 0},
			fields=["name", "file_name", "file_url", "file_size"],
		)
	]
	if reading.state in DONE:
		return reading.name
	words = mail.plain(comm.content or "")
	forwarded = mail.unwrap(words)
	_set(
		reading,
		state="Read",
		how="Mail",
		text=f"{comm.subject or ''}\n\n{words}".strip()[:MOST_TEXT],
		structured=json.dumps(
			{
				"mail": {
					"from_email": (comm.sender or "").lower() or None,
					"from_name": comm.sender_full_name,
					"to": comm.recipients,
					"cc": comm.cc,
					"subject": comm.subject,
					"date": str(comm.communication_date or ""),
					"direction": comm.sent_or_received,
				},
				"forwarded": forwarded,
				"attachments": [one for one in attachments if one],
			},
			default=str,
		),
		read_on=now_datetime(),
	)
	from onedesk.one_intake import language

	_set(reading, language=language.guess(words))
	return reading.name


def _worth_reading(file, content: str | None) -> bool:
	"""Not a signature's logo: a small picture, or one drawn inline in the
	message itself."""
	if read.extension(file.file_name) in read.IMAGES:
		if cint(file.file_size) < SIGNATURE or (file.file_url and file.file_url in (content or "")):
			return False
	return True


# ------------------------------------------------------------------ state


def _set(reading, **values) -> None:
	reading.update(values)
	reading.flags.ignore_permissions = True
	reading.save()
	frappe.db.commit()


def _failed(reading, raised: Exception) -> None:
	from onedesk.one_admin import faults

	if vision.credits_gone(raised):
		_set(reading, state="Waiting for Credits", error=str(raised)[:500])
	elif isinstance(raised, faults.Again) and cint(reading.tries) < TRIES:
		_set(reading, state="Queued", tries=cint(reading.tries) + 1, error=str(raised)[:500])
	else:
		frappe.log_error(title=f"Intake could not read {reading.name}")
		_set(reading, state="Failed", tries=cint(reading.tries) + 1, error=str(raised)[:500])


def again() -> None:
	"""Every quarter hour: readings that waited for credits or failed for a
	passing reason are tried again, and files and messages that were never
	read (they were there before Intake was) are caught up, a few at a time."""
	stale = frappe.utils.add_to_date(now_datetime(), minutes=-10)
	for held in frappe.get_all(
		"Reading",
		filters={"state": ["in", ("Queued", "Waiting for Credits")], "modified": ["<", stale]},
		fields=["name", "source_doctype", "source_name", "history"],
		limit=50,
	):
		_again(held.source_doctype, held.source_name, held.history)
	for name in unread_files(CATCH_UP):
		frappe.cache.set_value(f"one-intake-tried:{name}", 1, expires_in_sec=30 * 24 * 3600)
		later("read_file", f"file:{name}", name=name, history=1)
	for name in unread_mail(CATCH_UP):
		frappe.cache.set_value(f"one-intake-tried:{name}", 1, expires_in_sec=30 * 24 * 3600)
		later("read_mail", f"mail:{name}", name=name, history=1)


#: Files and messages caught up in one quarter hour.
CATCH_UP = 40


def _again(doctype: str, name: str, history: int) -> None:
	if doctype == "File":
		later("read_file", f"file:{name}", name=name, history=history)
	elif doctype == "Communication":
		later("read_mail", f"mail:{name}", name=name, history=history)


def unread_files(most: int) -> list[str]:
	"""Files with no Reading, leaving out pictures and sound (read only where
	OneAI is switched on, when they arrive) and those already tried."""
	skipped = ", ".join(frappe.db.escape(one) for one in SKIPPED | {"Communication"})
	media = " and ".join(f"f.file_name not like {frappe.db.escape('%.' + ext)}" for ext in read.IMAGES + read.SOUNDS)
	found = frappe.db.sql(
		f"""select f.name from `tabFile` f
		where f.is_folder = 0 and ifnull(f.one_deleted, 0) = 0 and f.content_hash is not null
		and ifnull(f.attached_to_doctype, '') not in ({skipped}) and {media}
		and not exists (select 1 from `tabReading` r where r.key = f.content_hash)
		order by f.creation desc limit %s""",
		(most * 3,),
		pluck=True,
	)
	return [name for name in found if not frappe.cache.get_value(f"one-intake-tried:{name}")][:most]


def unread_mail(most: int) -> list[str]:
	found = frappe.db.sql(
		"""select c.name from `tabCommunication` c
		where c.communication_medium = 'Email' and c.email_account is not null
		and not exists (select 1 from `tabReading` r
			where r.key = concat('mail-', md5(coalesce(nullif(c.message_id, ''), c.name))))
		order by c.creation desc limit %s""",
		(most * 3,),
		pluck=True,
	)
	return [name for name in found if not frappe.cache.get_value(f"one-intake-tried:{name}")][:most]
