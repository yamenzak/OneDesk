"""A conversation is its first message's Message-ID.

Found through `References` and `In-Reply-To`, as every mail client does. A
message whose references name nothing we hold starts a conversation of its
own. The subject is never a key: two unrelated "Invoice" threads are two
threads.
"""

import re

import frappe

#: A Message-ID as it appears in a header.
MESSAGE_ID = re.compile(r"<([^<>\s]+)>")


def ids(header: str | None) -> list[str]:
	"""The Message-IDs in a References or In-Reply-To header, in order,
	without their angle brackets, as Frappe stores them. Also reads them back
	from `one_references`, which holds them bare and space-separated: Frappe
	strips anything in angle brackets from a stored field as if it were HTML.
	Pure."""
	found = MESSAGE_ID.findall(header or "")
	return found or [
		one for one in (header or "").split() if "@" in one and "<" not in one and ">" not in one
	]


def stored(header: str | None) -> str | None:
	"""A header's Message-IDs as `one_references` keeps them. Pure."""
	return " ".join(ids(header)) or None


def pick(references: list[str], known: dict[str, str]) -> str | None:
	"""The thread of the earliest referenced message we hold. `known` maps a
	Message-ID we hold to its thread. Pure."""
	for one in references:
		if one in known:
			return known[one]
	return None


def thread_of(message_id: str | None, references: str | None) -> str | None:
	"""The thread a message joins: its earliest known ancestor's, or its own."""
	referenced = ids(references)
	if referenced:
		held = frappe.get_all(
			"Communication",
			filters={"message_id": ["in", referenced]},
			fields=["message_id", "one_thread"],
		)
		found = pick(referenced, {row.message_id: row.one_thread or row.message_id for row in held})
		if found:
			return found
	return (message_id or "").strip(" <>") or None


def adopt(doc, method=None) -> None:
	"""Communication after_insert: replies that arrived before this message
	join its thread. Folders are read one after another, so an answer in the
	Inbox is often read before the message it answers, in Sent."""
	if doc.communication_medium != "Email" or not doc.message_id or not doc.one_thread:
		return
	own = doc.message_id.strip(" <>")
	strays = {
		row.one_thread
		for row in frappe.get_all(
			"Communication",
			filters={"one_references": ["like", f"%{own}%"], "one_thread": ["!=", doc.one_thread]},
			fields=["one_thread", "one_references"],
		)
		if row.one_thread and own in ids(row.one_references)
	}
	if strays:
		frappe.db.set_value(
			"Communication",
			{"one_thread": ["in", list(strays)]},
			"one_thread",
			doc.one_thread,
			update_modified=False,
		)
