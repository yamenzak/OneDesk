"""What the browser asks for: the documents, and one document.

Read-only and open to anybody signed in. A person who is being asked to agree
to something has to be able to read it first, and somebody who agreed in March
has to be able to read what they agreed to — so a stored version can be fetched
by name as well.
"""

import frappe
from frappe import _

from . import assemble, gate
from .documents import PARTY


@frappe.whitelist(methods=["GET"])
def catalogue() -> dict:
	"""Every document, with its current version and who has to agree to it."""
	return {"party": PARTY, "documents": assemble.documents()}


@frappe.whitelist(methods=["GET"])
def document(key: str, version: str = "") -> dict:
	"""One document — the current text, or the exact text of an old version.

	An old version comes from `Legal Document Version`, which is written the
	first time anybody agrees to it. Asking for a version nobody ever agreed to
	is not an error worth an exception: it answers with the current one and says
	which it gave you.
	"""
	if version:
		stored = frappe.db.get_value(
			"Legal Document Version",
			f"{key}-{version}",
			["title", "version", "revision", "audience", "html"],
			as_dict=True,
		)
		if stored:
			return {"key": key, "party": PARTY, "historic": True, **stored}

	try:
		return {**assemble.render(key), "historic": False}
	except KeyError:
		frappe.throw(_("There is no such document."))


@frappe.whitelist(methods=["GET"])
def history(key: str = "") -> list[dict]:
	"""Every version this workspace has ever agreed to, newest first."""
	filters = {"document": key} if key else {}
	return frappe.get_all(
		"Legal Document Version",
		filters=filters,
		fields=["name", "document", "title", "version", "revision", "audience"],
		order_by="creation desc",
		ignore_permissions=True,
	)


@frappe.whitelist(methods=["GET"])
def overview() -> dict:
	"""Every document and where it stands: what the reader agreed to
	themselves, what the organisation agreed to and who agreed for it, and what
	is only published. Read from the rows the gate writes, never a second copy."""
	from onedesk.one import roles

	from .documents import DOCUMENTS

	def last(key: str, party: str) -> dict | None:
		filters = {"document": key, "party": party}
		if party == gate.USER:
			filters["user"] = frappe.session.user
		rows = frappe.get_all(
			"Legal Acceptance",
			filters=filters,
			fields=["version", "user", "accepted_on"],
			order_by="creation desc",
			limit=1,
			ignore_permissions=True,
		)
		if not rows:
			return None
		row = rows[0]
		return {
			"version": row.version,
			"owed": not gate.agreed(row.version, assemble.version_of(key)),
			"on": frappe.utils.formatdate(row.accepted_on),
			"by": frappe.utils.get_fullname(row.user) if party == gate.WORKSPACE else None,
		}

	documents = []
	for key, one in DOCUMENTS.items():
		version = assemble.version_of(key)
		parties = gate.AUDIENCE.get(one["audience"], ())
		title, summary = one["title"], one["summary"]
		documents.append(
			{
				"key": key,
				"title": _(title),
				"summary": _(summary),
				"version": version,
				"you": {"current": version, "owed": True, **(last(key, gate.USER) or {})}
				if gate.USER in parties
				else None,
				"organisation": {"current": version, "owed": True, **(last(key, gate.WORKSPACE) or {})}
				if gate.WORKSPACE in parties
				else None,
			}
		)
	return {"party": PARTY, "documents": documents, "admin": roles.administers(), "may_bind": gate._may_bind()}
