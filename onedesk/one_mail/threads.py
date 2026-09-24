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
	without their angle brackets, as Frappe stores them. Pure."""
	return MESSAGE_ID.findall(header or "")


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
