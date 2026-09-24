"""Finding a document by what is written in it.

A FULLTEXT index over every Reading, and three places that ask it: the awesome
bar (Ctrl+K), OneCloud's search box and OneMail's. Each hit is checked against
the reader's own right to open the file or the message it came from.

Frappe's global search is left alone on purpose: it checks only whether a
person may read a *doctype*, never which record. Document text put there would
show one employee's payslip to anybody who may read any document.
"""

import re
from typing import Annotated

import frappe
from frappe import _

from onedesk.one_intake import pipeline

INDEX = "one_reading_text"

#: Words the index skips anyway; asking for them with `+` finds nothing.
SKIP = frozenset(
	"the and for are with this that from you your der die das und ist mit für von den dem ein eine les des une pour"
	.split()
)

#: Characters shown before the first match, and in all. Little before it, so
#: the word found is in sight even in a narrow column.
BEFORE, WIDTH = 24, 160


def index() -> None:
	"""after_migrate: the FULLTEXT index Frappe's schema cannot declare."""
	if not frappe.db.table_exists("Reading"):
		return
	if not frappe.db.sql(f"show index from `tabReading` where Key_name = '{INDEX}'"):
		frappe.db.sql_ddl(f"alter table `tabReading` add fulltext index `{INDEX}` (`title`, `text`)")


def words(text: str) -> list[str]:
	"""What to ask the index for: whole words of three letters or more, the
	operators FULLTEXT would read stripped out. Pure."""
	found = re.findall(r"\w{3,}", (text or "").lower())
	return [word for word in dict.fromkeys(found) if word not in SKIP][:8]


def found(text: str, most: int = 60) -> list[dict]:
	"""Readings containing every word, best first, with the line around the
	first one."""
	asked = words(text)
	if not asked:
		return []
	boolean = " ".join(f"+{word}*" for word in asked)
	return frappe.db.sql(
		"""select name, title, part, part_of, message_id, source_doctype, source_name, `key`,
			match(title, text) against (%(q)s in boolean mode) as score,
			substring(text, greatest(1, locate(%(first)s, text) - %(before)s), %(width)s) as snippet
		from `tabReading`
		where state in ('Read', 'Understood') and match(title, text) against (%(q)s in boolean mode)
		order by score desc limit %(most)s""",
		{"q": boolean, "first": asked[0], "before": BEFORE, "width": WIDTH, "most": most},
		as_dict=True,
	)


def snippet(text: str) -> str:
	return "…" + " ".join((text or "").split()) + "…" if text else ""


def root_of(hit: dict) -> dict:
	"""The top Reading a part belongs to: a page range of a scan, a file in a
	zip, a message inside a message."""
	seen = 0
	while hit.get("part_of") and seen < pipeline.DEEPEST + 2:
		parent = frappe.db.get_value(
			"Reading", hit["part_of"], ["name", "title", "part_of", "message_id", "source_doctype", "source_name", "key"], as_dict=True
		)
		if not parent:
			break
		hit, seen = {**parent, "snippet": hit.get("snippet"), "part": hit.get("title")}, seen + 1
	return hit


def files_of(hit: dict) -> list[dict]:
	"""The Files holding this content that the reader may open."""
	from onedesk.one_storage import namespace as ns

	if hit.get("source_doctype") != "File":
		return []
	rows = frappe.get_all("File", filters={"content_hash": hit["key"], "one_deleted": 0, "is_folder": 0}, fields=ns.FIELDS, limit=20)
	# One letter cut from a batch scan is a file of its own, named by its reading.
	rows += frappe.get_all("File", filters={"one_reading": hit.get("name"), "one_deleted": 0, "is_folder": 0}, fields=ns.FIELDS, limit=5) if hit.get("name") else []
	if not rows and hit.get("source_name"):
		rows = frappe.get_all("File", filters={"name": hit["source_name"], "one_deleted": 0}, fields=ns.FIELDS)
	return [row for row in rows if ns.may(row)]


def messages_of(hit: dict) -> list[str]:
	"""The messages holding this reading that the reader may open: the
	Communication permission hook is OneMail's, holders only."""
	if hit.get("source_doctype") == "File" and hit.get("source_name"):
		attached = frappe.db.get_value("File", hit["source_name"], ["attached_to_doctype", "attached_to_name"], as_dict=True)
		names = [attached.attached_to_name] if attached and attached.attached_to_doctype == "Communication" else []
	elif hit.get("message_id"):
		names = frappe.get_all("Communication", filters={"message_id": hit["message_id"]}, pluck="name", limit=10)
	else:
		names = [hit.get("source_name")] if hit.get("source_doctype") == "Communication" else []
	return [name for name in names if name and frappe.has_permission("Communication", "read", name)]


# ------------------------------------------------------------------ the three places


def awesomebar(txt: str) -> list[dict]:
	"""The awesome bar's "In documents": files and messages whose words match."""
	out = []
	# A hit on the letter inside a batch scan says more than one on the whole scan.
	for hit in sorted(found(txt, 30), key=lambda one: not one.get("part_of")):
		top = root_of(hit)
		where = f", {hit['part']}" if hit.get("part_of") and hit.get("part") else ""
		for file in [one for one in files_of(top) if one.attached_to_doctype != "Communication"][:1]:
			out.append(
				{
					"label": _("{0} (in documents)").format(file.file_name + where),
					"description": snippet(hit.get("snippet")),
					"route": _file_route(file),
					"index": 60,
				}
			)
		for name in messages_of(top)[:1]:
			thread, account = frappe.db.get_value("Communication", name, ["one_thread", "email_account"])
			out.append(
				{
					"label": _("{0} (in mail)").format(top.get("title") or name),
					"description": snippet(hit.get("snippet")),
					"route": f"/app/onemail?box={account}&thread={thread or name}",
					"index": 55,
				}
			)
		out = _once(out)
		if len(out) >= 12:
			break
	return out


def _once(items: list[dict]) -> list[dict]:
	"""The best hit for each place: a scan found by two of its letters is one row."""
	seen, out = set(), []
	for one in items:
		if one["route"] not in seen:
			seen.add(one["route"])
			out.append(one)
	return out


def _file_route(file) -> str:
	if file.attached_to_doctype and file.attached_to_name and file.attached_to_doctype != "Communication":
		return f"/app/{frappe.scrub(file.attached_to_doctype).replace('_', '-')}/{file.attached_to_name}"
	return f"/app/onecloud?node={file.folder}&file={file.name}"


def in_files(text: str, under: list[str] | None = None, most: int = 100) -> list[dict]:
	"""OneCloud's search, by content: what the reader may open, as nodes, each
	with the words it was found by. `under` keeps only what is in those folders."""
	from onedesk.one_storage import namespace as ns

	out, seen = [], set()
	folders = ns._folders()
	for hit in found(text, most):
		for file in files_of(root_of(hit)):
			if file.name in seen or file.attached_to_doctype in ns.UNLISTED:
				continue
			if under is not None and file.folder not in under:
				continue
			seen.add(file.name)
			out.append(
				{
					**ns.node(file),
					"found": snippet(hit.get("snippet")),
					"where": ns._where_label(file, folders, frappe.session.user),
					"parent": file.folder,
				}
			)
	return out[:most]


def in_mail(account: str, text: str, most: int = 200) -> list[str]:
	"""OneMail's search, by content: the messages of one mailbox whose own
	words or attachments match."""
	names = []
	for hit in found(text, most):
		for name in messages_of(root_of(hit)):
			if frappe.db.get_value("Communication", name, "email_account") == account:
				names.append(name)
	return list(dict.fromkeys(names))


# ------------------------------------------------------------------ for OneAI


#: How many documents OneAI is shown, at most.
MOST_FOUND = 10


def find_documents(
	words: Annotated[str, "Words the document would contain. Include the words in the document's own language as well as the reader's: Nebenkostenabrechnung for a heating bill, فاتورة for an invoice."],
	kind: Annotated[str, "Only this kind of document: Invoice, Receipt, Reminder, Contract, Letter, Payslip, Sick Note and so on."] | None = None,
	party: Annotated[str, "Only documents from or about this supplier, customer, person or company."] | None = None,
	since: Annotated[str, "Only documents dated on or after this day, YYYY-MM-DD."] | None = None,
	until: Annotated[str, "Only documents dated on or before this day, YYYY-MM-DD."] | None = None,
) -> dict:
	"""Find documents and messages by what is written in them: letters,
	invoices, receipts, contracts, scans and mail. Answers each with what it
	is, who it is from, its date, number and amount, one sentence about it,
	the passage that matched and a link to open it. Only what the reader may
	open is found. For a question about amounts, add up the amounts found
	rather than quoting a passage."""
	asked = [word for word in re.findall(r"\w{3,}", (words or "").lower()) if word not in SKIP][:12]
	# A batch scan is found through the letters cut from it, not beside them.
	conditions, values = ["state in ('Read', 'Understood')", "name not in (select part_of from `tabReading` where ifnull(part_of, '') != '')"], {}
	if asked:
		conditions.append("match(title, text) against (%(q)s in boolean mode)")
		values["q"] = " ".join(f"{word}*" for word in asked)
	if kind:
		conditions.append("kind = %(kind)s")
		values["kind"] = kind
	if since:
		conditions.append("issued_on >= %(since)s")
		values["since"] = since
	if until:
		conditions.append("issued_on <= %(until)s")
		values["until"] = until
	if party:
		conditions.append("name in (select parent from `tabReading Party` where party_name like %(party)s or matched_name like %(party)s)")
		values["party"] = f"%{party}%"
	if len(conditions) == 2:
		return {"documents": [], "said": "Say some words, a kind, a party or dates to look for."}
	score = "match(title, text) against (%(q)s in boolean mode)" if asked else "0"
	rows = frappe.db.sql(
		f"""select name, title, kind, number, issued_on, gross, currency, summary, part, part_of, message_id,
			source_doctype, source_name, `key`, {score} as score,
			substring(text, greatest(1, locate(%(first)s, text) - %(before)s), %(width)s) as snippet
		from `tabReading` where {" and ".join(conditions)}
		order by score desc, issued_on desc limit 60""",
		{**values, "first": asked[0] if asked else "", "before": BEFORE, "width": WIDTH},
		as_dict=True,
	)
	out = []
	for row in rows:
		top = root_of(row)
		files = [one for one in files_of({**top, "name": row.name}) if one.get("attached_to_doctype") != "Communication"]
		messages = messages_of(top)
		if not files and not messages:
			continue
		party_name = frappe.db.get_value("Reading Party", {"parent": row.name, "role": ["in", ("Sender", "Holder", "Paid To")]}, "party_name")
		out.append(
			{
				"title": row.title,
				"kind": row.kind,
				"from": party_name,
				"date": str(row.issued_on) if row.issued_on else None,
				"number": row.number,
				"amount": row.gross,
				"currency": row.currency,
				"about": row.summary,
				"passage": snippet(row.snippet) if asked else None,
				"link": _file_route(files[0]) if files else f"/app/onemail?thread={frappe.db.get_value('Communication', messages[0], 'one_thread') or messages[0]}",
			}
		)
		if len(out) >= MOST_FOUND:
			break
	return {"documents": out}


def about(doctype: str, name: str, most: int = 12) -> list[dict]:
	"""The documents a record was filed with, linked to or made from, as
	OneAI's record memory tells them: what each is and what it still asks.
	Only those the reader may open."""
	readings = set(
		frappe.get_all("Intake Action", filters={"target_doctype": doctype, "target_name": name, "level": "Done"}, pluck="reading", limit=100)
	)
	readings |= set(frappe.get_all("Reading Party", filters={"matched_doctype": doctype, "matched_name": name}, pluck="parent", limit=100))
	readings.discard(None)
	if not readings:
		return []
	rows = frappe.get_all(
		"Reading",
		filters={"name": ["in", list(readings)], "state": "Understood"},
		fields=["name", "title", "kind", "issued_on", "number", "gross", "currency", "summary", "sensitivity", "source_doctype", "source_name", "key", "message_id", "part_of"],
		order_by="issued_on desc",
		limit=most * 3,
	)
	out = []
	for row in rows:
		top = root_of(dict(row))
		if not files_of({**top, "name": row.name}) and not messages_of(top):
			continue
		asks = frappe.get_all("Reading Ask", filters={"parent": row.name}, fields=["what", "detail", "by_date"])
		out.append(
			{
				"document": row.title,
				"kind": row.kind,
				"date": str(row.issued_on) if row.issued_on else None,
				"number": row.number,
				"amount": row.gross,
				"currency": row.currency,
				"about": row.summary if row.sensitivity in (None, "", "Ordinary") else None,
				"asks": [f"{one.what}: {one.detail or ''} {('by ' + str(one.by_date)) if one.by_date else ''}".strip() for one in asks],
			}
		)
		if len(out) >= most:
			break
	return out
