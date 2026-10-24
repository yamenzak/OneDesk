"""Search by meaning: documents, mail and records as vectors.

Each source (a document OneIntake read, a message, a record people search
for) is cut into pieces, each piece embedded once through the account and
kept as an `AI Chunk`; a search embeds the question and scans for the
nearest. After OneApp's `oneai/index.py`. README, index.py.
"""

import array
import base64
import hashlib
import math
from operator import mul

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

#: Pieces one search compares, newest first. Measured: about 60ms per 2,000
#: in pure Python, held unpacked between searches.
MOST_SCANNED = 12_000

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

SOURCES = (*DOCUMENTS, *RECORDS)

WORDS = ("Data", "Small Text", "Text", "Long Text", "Text Editor", "Select", "Link", "Date", "Currency")

NEVER = ("naming_series", "amended_from", "company")

_held: dict = {}


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


def pack(values: list[float]) -> str:
	"""A vector as base64 of normalised float32, so a comparison is a dot product. Pure."""
	length = math.sqrt(sum(one * one for one in values)) or 1.0
	return base64.b64encode(array.array("f", [one / length for one in values]).tobytes()).decode()


def unpack(blob: str) -> array.array:
	found = array.array("f")
	found.frombytes(base64.b64decode(blob or ""))
	return found


def digest(text: str) -> str:
	return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:32]


def closest(query: array.array, rows: list[tuple], most: int) -> list[tuple[float, dict]]:
	"""The rows nearest the query, best first: rows are (vector, meta). Pure."""
	scored = [(sum(map(mul, query, vector)), meta) for vector, meta in rows if len(vector) == len(query)]
	scored.sort(key=lambda one: one[0], reverse=True)
	return scored[:most]


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
	"""Index one source as it reads now; whether a call was made. A source
	whose text has not changed costs nothing."""
	if not frappe.db.exists(doctype, name):
		forget(doctype, name)
		return False
	title, text = said_of(doctype, name)
	parts = pieces(text)
	if not parts:
		forget(doctype, name)
		return False
	held = frappe.get_all(
		CHUNK,
		filters={"source_doctype": doctype, "source_name": name},
		fields=["name", "part", "digest", "model"],
		order_by="part asc",
	)
	if [one.digest for one in held] == [digest(one) for one in parts]:
		return False
	said = embedded(parts)
	if len(said["vectors"]) != len(parts):
		return False
	forget(doctype, name)
	for at, (part, vector) in enumerate(zip(parts, said["vectors"], strict=True)):
		frappe.get_doc(
			{
				"doctype": CHUNK,
				"source_doctype": doctype,
				"source_name": name,
				"part": at,
				"title": (title or name)[:140],
				"text": part,
				"digest": digest(part),
				"model": said["model"],
				"vector": pack(vector),
			}
		).db_insert()
	_held.pop(frappe.local.site, None)
	return True


def forget(doctype: str, name: str) -> None:
	frappe.db.delete(CHUNK, {"source_doctype": doctype, "source_name": name})


def changed(doc, method=None) -> None:
	"""on_update and after_insert on every source: index it again, after the
	save is committed, once however often it is saved in a minute."""
	if doc.doctype not in SOURCES or not on():
		return
	frappe.enqueue(
		"onedesk.one_ai.index.refresh",
		queue="long",
		doctype=doc.doctype,
		name=doc.name,
		job_id=f"one_index::{doc.doctype}::{doc.name}",
		deduplicate=True,
		enqueue_after_commit=True,
	)


def removed(doc, method=None) -> None:
	if doc.doctype in SOURCES:
		forget(doc.doctype, doc.name)


def refresh(doctype: str, name: str) -> None:
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
	"""Every quarter of an hour: the newest sources with no pieces yet."""
	if not on():
		return 0
	done = 0
	for doctype in SOURCES:
		if not frappe.db.table_exists(doctype):
			continue
		rows = frappe.db.sql(
			f"""select name from `tab{doctype}` src
			where not exists (select 1 from `tabAI Chunk` c where c.source_doctype = %(doctype)s and c.source_name = src.name)
			{_not_unread_mail(doctype)}
			order by modified desc limit %(most)s""",
			{"doctype": doctype, "most": CATCH_UP - done, "off": _off_mailboxes()},
		)
		for (name,) in rows:
			try:
				done += remember(doctype, name)
			except Exception:
				frappe.log_error(title="Search by meaning could not index", reference_doctype=doctype, reference_name=name)
				return done
			if done >= CATCH_UP:
				return done
	return done


def _rows(model: str | None) -> list[tuple]:
	"""Every piece's vector with what it points at, newest first, held
	between searches and read again only when the index changed."""
	site = frappe.local.site
	stamp = frappe.db.sql(f"select count(*), max(modified) from `tab{CHUNK}`")[0]
	held = _held.get(site)
	if held and held["stamp"] == stamp:
		return held["rows"]
	rows = frappe.get_all(
		CHUNK,
		filters={"model": model} if model else {},
		fields=["source_doctype", "source_name", "part", "title", "text", "vector"],
		order_by="modified desc",
		limit_page_length=MOST_SCANNED,
	)
	unpacked = [
		(unpack(row.pop("vector")), row)
		for row in rows
	]
	_held[site] = {"stamp": stamp, "rows": unpacked}
	return unpacked


def nearest(text: str, doctypes: list[str] | tuple | None = None, most: int = 10) -> list[dict]:
	"""The pieces closest in meaning to `text` that the reader may open, the
	best piece of each source once, best first."""
	if not on() or not (text or "").strip():
		return []
	said = embedded([text[:2000]])
	if not said["vectors"]:
		return []
	query = unpack(pack(said["vectors"][0]))
	rows = [one for one in _rows(said["model"]) if not doctypes or one[1]["source_doctype"] in doctypes]
	out, seen = [], set()
	for score, meta in closest(query, rows, most * 6):
		key = (meta["source_doctype"], meta["source_name"])
		if key in seen or not _may(*key):
			continue
		seen.add(key)
		out.append({**meta, "score": round(score, 4)})
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
		from onedesk.one_intake import search

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
