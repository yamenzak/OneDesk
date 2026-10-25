"""Search on the workspace's own AI Search instance (docs/AICENTER.md,
Search): records written as Markdown under `search/` in its R2 prefix,
searched through the account, and shown only where the reader may open
them. Until the account says there is an instance, nothing is written and
`index.py` answers."""

from urllib.parse import quote, unquote

import frappe

from onedesk.one import account

PREFIX = "search/"

# What a workspace with no instance is told, and how long the account's
# answer to whether there is one is believed.
NONE = "NoSearch"
BELIEVED = 60 * 60
CACHE = "one_ai_search_live"

# Hits asked for per hit shown, since some go to permissions.
SPARE = 3


def live() -> bool:
	"""Whether this workspace has its own instance, as the account last said."""
	if not account.configured():
		return False
	held = frappe.cache.get_value(CACHE)
	if held is None:
		try:
			held = int(bool((account.ask("onedesk.one_admin.proxy.ai_search_state") or {}).get("live")))
		except Exception:
			held = 0
		frappe.cache.set_value(CACHE, held, expires_in_sec=BELIEVED)
	return bool(held)


def key_of(doctype: str, name: str) -> str:
	"""Where a record's Markdown lives. Pure."""
	return f"{PREFIX}{quote(frappe.scrub(doctype), safe='')}/{quote(str(name), safe='')}.md"


def source_of(key: str) -> tuple[str, str] | None:
	"""The record a key is for, from the doctypes that are searched. Pure but
	for the list of them."""
	from onedesk.one_ai import index

	if not key.startswith(PREFIX) or not key.endswith(".md"):
		return None
	scrubbed, _, name = key[len(PREFIX) : -3].partition("/")
	doctype = next((one for one in index.SOURCES if frappe.scrub(one) == unquote(scrubbed)), None)
	return (doctype, unquote(name)) if doctype and name else None


def _title(doctype: str, name: str) -> str:
	field = frappe.get_meta(doctype).title_field
	return str((frappe.db.get_value(doctype, name, field) if field else None) or name)


def markdown(title: str, text: str) -> str:
	"""A record as AI Search reads it. Pure."""
	return f"# {title.strip()}\n\n{text.strip()}\n" if text.strip() else ""


def write(doctype: str, name: str) -> None:
	"""A record's Markdown, written again as it reads now, or taken away when
	there is nothing left to find."""
	from onedesk.one_ai import index
	from onedesk.one_storage import store

	if not live():
		return
	title, text = index.said_of(doctype, name) if frappe.db.exists(doctype, name) else ("", "")
	said = markdown(title or name, text)
	if not said:
		drop(doctype, name)
		return
	store.put(key_of(doctype, name), said.encode())


def drop(doctype: str, name: str) -> None:
	if live():
		account.drop(key_of(doctype, name))


def find(text: str, doctypes: list[str] | tuple | None = None, most: int = 10, mode: str = "meaning") -> list[dict] | None:
	"""The records the instance finds that the reader may open, best first,
	in `index.nearest`'s shape; None when there is no instance."""
	from onedesk.one_ai import index, run

	if not live() or not (text or "").strip():
		return None
	try:
		said = run.search(text[:2000], mode, most * SPARE)
	except Exception as raised:
		if getattr(raised, "said", None) == NONE:
			frappe.cache.set_value(CACHE, 0, expires_in_sec=BELIEVED)
			return None
		raise
	out, seen = [], set()
	for hit in said.get("hits") or []:
		source = source_of(hit.get("key") or "")
		if not source or source in seen or (doctypes and source[0] not in doctypes) or not index._may(*source):
			continue
		seen.add(source)
		out.append({"source_doctype": source[0], "source_name": source[1], "text": hit.get("text") or "", "score": hit.get("score"), "title": _title(*source)})
		if len(out) >= most:
			break
	return out
