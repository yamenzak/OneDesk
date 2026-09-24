"""Finding a document by what is written in it.

A FULLTEXT index over every Reading, and three places that ask it: the awesome
bar (Ctrl+K), OneCloud's search box and OneMail's. Each hit is checked against
the reader's own right to open the file or the message it came from.

Frappe's global search is left alone on purpose: it checks only whether a
person may read a *doctype*, never which record. Document text put there would
show one employee's payslip to anybody who may read any document.
"""

import re

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
		where state = 'Read' and match(title, text) against (%(q)s in boolean mode)
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
