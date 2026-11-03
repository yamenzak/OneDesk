"""Search by meaning: documents, mail and records cut into pieces, each
embedded once and kept in the workspace's index on R2 (one_ai/vectors.py),
with an `AI Chunk` row here saying it is there. AGENTS.md, index.py."""

import hashlib
import math

import frappe
from frappe.utils import strip_html_tags

from onedesk.one import account, apps

CHUNK = "AI Chunk"

#: Characters in one piece, and how much each repeats of the one before, so
#: a sentence cut in two is whole in one of them.
PIECE, OVERLAP = 1500, 200

#: Pieces of one source: past this it is a manual, and what is searched for
#: is nearly always in its first pages.
MOST_PIECES = 24

#: Sources the catch-up indexes in one go.
CATCH_UP = 150

#: Records people look for by what they are about, described by their
#: title and words fields. Documents and mail are indexed by what they say.
RECORDS = (
	"Customer",
	"Supplier",
	"Lead",
	"Opportunity",
	"Contact",
	"Project",
	"Task",
	"Item",
	"Quotation",
	"Sales Order",
	"Sales Invoice",
	"Purchase Order",
	"Purchase Invoice",
	"Issue",
)

DOCUMENTS = ("Reading", "Communication")

#: What OneAI was told to remember and what the workspace wrote down for it,
#: found by meaning by `recall` alone, never among the records searched.
RECALLED = ("AI Memory", "AI Knowledge")

SEARCHED = (*DOCUMENTS, *RECORDS)

SOURCES = (*SEARCHED, *RECALLED)

WORDS = ("Data", "Small Text", "Text", "Long Text", "Text Editor", "Select", "Link", "Date", "Currency")

NEVER = ("naming_series", "amended_from", "company")

def on() -> bool:
	"""Whether this workspace searches by meaning: OneAI on, and an account
	to embed through."""
	return apps.ai_on() and account.configured()


def pieces(text: str) -> list[str]:
	"""Text cut into overlapping pieces, at a space where there is one. Pure."""
	text = " ".join((text or "").split())
	out, at = [], 0
	while at < len(text) and len(out) < MOST_PIECES:
		end = min(at + PIECE, len(text))
		if end < len(text):
			space = text.rfind(" ", at + PIECE // 2, end)
			end = space if space > 0 else end
		out.append(text[at:end].strip())
		if end >= len(text):
			break
		at = max(end - OVERLAP, at + 1)
	return [one for one in out if one]


def normal(values: list[float]) -> list[float]:
	"""A vector at length one, so near in meaning is near in distance. Pure."""
	length = math.sqrt(sum(one * one for one in values)) or 1.0
	return [one / length for one in values]


def digest(text: str) -> str:
	return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:32]


def embedded(texts: list[str]) -> dict:
	"""Texts as vectors, through the account, in batches it takes."""
	vectors, model = [], None
	for at in range(0, len(texts), 32):
		said = account.ask("onedesk.one_admin.proxy.ai_embed", texts=texts[at : at + 32]) or {}
		vectors += said.get("vectors") or []
		model = said.get("model") or model
	return {"vectors": vectors, "model": model}


def _indexed_mail(doctype: str, name: str) -> bool:
	"""Mail is embedded only from a mailbox OneAI reads on its own, so a
	mailbox nobody switched on costs nothing here (one_mail/gate.py)."""
	from onedesk.one_mail import gate

	account = gate.account_of(doctype, name)
	return not account or account not in gate.not_indexed()


def said_of(doctype: str, name: str) -> tuple[str, str]:
	"""A source's title and the text that is embedded for it."""
	if doctype in ("Reading", "Communication") and not _indexed_mail(doctype, name):
		return "", ""
	if doctype == "Reading":
		held = frappe.db.get_value(
			"Reading", name, ["title", "summary", "text", "state", "kind"], as_dict=True
		)
		if not held or held.state not in ("Read", "Understood"):
			return "", ""
		return held.title or name, "\n".join(one for one in (held.title, held.kind, held.summary, held.text) if one)
	if doctype == "Communication":
		held = frappe.db.get_value(
			"Communication",
			name,
			["subject", "content", "communication_medium", "sender_full_name", "sender"],
			as_dict=True,
		)
		if not held or held.communication_medium != "Email":
			return "", ""
		from onedesk.one_mail import linking

		body = strip_html_tags(linking.fresh_part(held.content or ""))
		return held.subject or name, f"{held.subject or ''}\nFrom {held.sender_full_name or held.sender or ''}\n{body}"
	doc = frappe.get_doc(doctype, name)
	meta = doc.meta
	title = str(doc.get(meta.title_field) or name) if meta.title_field else name
	lines = [f"{frappe._(doctype)}: {title}"]
	for df in meta.fields:
		if df.fieldtype not in WORDS or df.fieldname in NEVER or df.hidden:
			continue
		value = doc.get(df.fieldname)
		if value in (None, "", 0):
			continue
		lines.append(f"{df.label or df.fieldname}: {strip_html_tags(str(value))[:400]}")
	return title, "\n".join(lines)


def remember(doctype: str, name: str) -> bool:
	"""Index one source as it reads now; whether a call was made."""
	return bool(remember_many([(doctype, name)]))


def remember_many(sources: list[tuple[str, str]]) -> int:
	"""Index these sources as they read now, in one embedding call and one
	write to the index; how many were embedded. A source whose text has not
	changed costs nothing, and one with nothing left to find is forgotten."""
	from onedesk.one_ai import vectors

	gone, wanted = [], []
	for doctype, name in dict.fromkeys(tuple(one) for one in sources):
		if not frappe.db.exists(doctype, name):
			gone.append((doctype, name))
			continue
		title, text = said_of(doctype, name)
		parts = pieces(text)
		if not parts:
			gone.append((doctype, name))
			continue
		held = frappe.get_all(
			CHUNK,
			filters={"source_doctype": doctype, "source_name": name},
			fields=["digest"],
			order_by="part asc",
			pluck="digest",
		)
		if held != [digest(one) for one in parts]:
			wanted.append((doctype, name, title or name, parts))
	forget_all(gone)
	if not wanted:
		return 0
	said = embedded([part for *_head, parts in wanted for part in parts])
	if len(said["vectors"]) != sum(len(parts) for *_head, parts in wanted):
		return 0
	rows, at = [], 0
	for doctype, name, title, parts in wanted:
		for part_at, part in enumerate(parts):
			rows.append(
				{
					"source_doctype": doctype,
					"source_name": name,
					"part": part_at,
					"title": title[:140],
					"text": part,
					"model": said["model"] or "",
					"vector": normal(said["vectors"][at]),
				}
			)
			at += 1
	vectors.put_many([(doctype, name) for doctype, name, *_rest in wanted], rows)
	for doctype, name, title, parts in wanted:
		frappe.db.delete(CHUNK, {"source_doctype": doctype, "source_name": name})
		for part_at, part in enumerate(parts):
			frappe.get_doc(
				{
					"doctype": CHUNK,
					"source_doctype": doctype,
					"source_name": name,
					"part": part_at,
					"title": title[:140],
					"digest": digest(part),
					"model": said["model"],
				}
			).db_insert()
	return len(wanted)


def forget(doctype: str, name: str) -> None:
	forget_all([(doctype, name)])


def forget_all(sources: list[tuple[str, str]]) -> None:
	"""These sources taken out of the index, and out of what says they are in it."""
	sources = [tuple(one) for one in sources if frappe.db.exists(CHUNK, {"source_doctype": one[0], "source_name": one[1]})]
	if not sources:
		return
	from onedesk.one_ai import vectors

	try:
		vectors.drop(sources)
	except Exception:
		frappe.log_error(title="Search could not forget", message=repr(sources[:20]))
	for at in range(0, len(sources), 200):
		for doctype, name in sources[at : at + 200]:
			frappe.db.delete(CHUNK, {"source_doctype": doctype, "source_name": name})


#: Sources saved since the index last caught up with them, as `doctype\0name`.
DIRTY = "one_index_dirty"

#: Sources one round of `flush` embeds and writes together.
FLUSHED = 100


def changed(doc, method=None) -> None:
	"""on_update and after_insert on every source: marked to be indexed again,
	and one job queued after commit for all of them, however many are saved.
	A job a record would fill frappe's queue on an import of thousands, and
	each one would write to R2 on its own."""
	if doc.doctype not in SOURCES or not on():
		return
	frappe.cache.sadd(DIRTY, f"{doc.doctype}\0{doc.name}")
	frappe.enqueue(
		"onedesk.one_ai.index.flush",
		queue="long",
		job_id="one_index_flush",
		deduplicate=True,
		enqueue_after_commit=True,
	)


def removed(doc, method=None) -> None:
	if doc.doctype in SOURCES and frappe.db.exists(CHUNK, {"source_doctype": doc.doctype, "source_name": doc.name}):
		forget(doc.doctype, doc.name)


def flush() -> int:
	"""The sources saved since, a hundred at a time, until none are left;
	how many were embedded. The catch-up runs it too, for any marked while
	the last one was finishing."""
	done = 0
	while True:
		batch = [one for one in (frappe.cache.spop(DIRTY) for _ in range(FLUSHED)) if one]
		if not batch:
			return done
		sources = [tuple((one.decode() if isinstance(one, bytes) else one).split("\0", 1)) for one in batch]
		try:
			done += remember_many(sources)
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			frappe.log_error(title="Search by meaning could not index", message=repr(sources[:20]))
			return done


def refresh(doctype: str, name: str) -> None:
	"""A job queued, one a record, before `flush` took their place."""
	try:
		remember(doctype, name)
	except Exception:
		frappe.log_error(title="Search by meaning could not index", reference_doctype=doctype, reference_name=name)


def _off_mailboxes() -> list[str]:
	from onedesk.one_mail import gate

	return gate.not_indexed() or ["\0"]


def _not_unread_mail(doctype: str) -> str:
	"""Leaves out mail from mailboxes that are not embedded, so they never
	crowd the newest rows the catch-up looks at."""
	if doctype == "Communication":
		return "and coalesce(src.email_account, '') not in %(off)s"
	if doctype == "Reading":
		return """and not (src.source_doctype = 'Communication' and src.source_name in
				(select m.name from `tabCommunication` m where m.email_account in %(off)s))
			and not (src.source_doctype = 'File' and src.source_name in
				(select f.name from `tabFile` f join `tabCommunication` m
					on f.attached_to_doctype = 'Communication' and f.attached_to_name = m.name
				where m.email_account in %(off)s))"""
	return ""


def catch_up() -> int:
	"""Every quarter of an hour: what was saved and is still marked, then the
	newest sources with no pieces yet."""
	if not on():
		return 0
	done = flush()
	for doctype in SOURCES:
		if done >= CATCH_UP:
			return done
		if not frappe.db.table_exists(doctype):
			continue
		rows = frappe.db.sql(
			f"""select name from `tab{doctype}` src
			where not exists (select 1 from `tabAI Chunk` c where c.source_doctype = %(doctype)s and c.source_name = src.name)
			{_not_unread_mail(doctype)}
			order by modified desc limit %(most)s""",
			{"doctype": doctype, "most": CATCH_UP - done, "off": _off_mailboxes()},
		)
		if not rows:
			continue
		try:
			done += remember_many([(doctype, name) for (name,) in rows])
		except Exception:
			frappe.log_error(title="Search by meaning could not index", reference_doctype=doctype)
			return done
		if done >= CATCH_UP:
			return done
	return done


def nearest(text: str, doctypes: list[str] | tuple | None = None, most: int = 10) -> list[dict]:
	"""The pieces closest in meaning to `text` that the reader may open, the
	best piece of each source once, best first."""
	if not on() or not (text or "").strip():
		return []
	doctypes = doctypes or SEARCHED
	from onedesk.one_ai import vectors

	said = embedded([text[:2000]])
	if not said["vectors"]:
		return []
	out, seen = [], set()
	for meta in vectors.find(normal(said["vectors"][0]), text[:500], doctypes, most):
		key = (meta["source_doctype"], meta["source_name"])
		if key in seen or not _may(*key):
			continue
		seen.add(key)
		out.append(meta)
		if len(out) >= most:
			break
	return out


def _may(doctype: str, name: str) -> bool:
	"""Whether the reader may open what a piece came from. A document is the
	reader's when its file or its message is, and never from a mailbox OneAI
	is turned off for."""
	from onedesk.one_mail import gate

	if doctype in ("Reading", "Communication", "File") and not gate.readable(doctype, name):
		return False
	if doctype == "Reading":
		from onedesk.one_ai.reading import search

		held = frappe.db.get_value(
			"Reading", name, ["name", "part_of", "message_id", "source_doctype", "source_name", "key"], as_dict=True
		)
		if not held:
			return False
		top = search.root_of(dict(held))
		return bool(search.files_of(top) or search.messages_of(top))
	try:
		return bool(frappe.has_permission(doctype, "read", doc=name))
	except frappe.DoesNotExistError:
		return False
