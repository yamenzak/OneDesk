"""What the browser asks for: the documents, and one document.

Read-only and open to anybody signed in. A person who is being asked to agree
to something has to be able to read it first, and somebody who agreed in March
has to be able to read what they agreed to — so a stored version can be fetched
by name as well.
"""

import re

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
			"owed": False,
			"changed": not gate.agreed(row.version, assemble.version_of(key)),
			"effective": gate.effective(key),
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
	return {
		"party": PARTY,
		"documents": documents,
		"admin": roles.administers(),
		"may_bind": gate._may_bind(),
		"sees_acceptances": _sees_acceptances(),
	}


def _sees_acceptances() -> bool:
	"""A workspace administrator, or a role given Who Agreed (abilities.py)."""
	from onedesk.one import abilities

	return abilities.may("Legal Acceptance", "legal_acceptances")


@frappe.whitelist(methods=["GET"])
def acceptances(key: str) -> list[dict]:
	"""Everybody in the workspace who agreed to one agreement, newest first,
	for whoever may see that."""
	if not _sees_acceptances():
		frappe.throw(_("Your role doesn't allow seeing who agreed."), frappe.PermissionError)
	rows = frappe.get_all(
		"Legal Acceptance",
		filters={"document": key},
		fields=["user", "party", "version", "accepted_on"],
		order_by="accepted_on desc",
		limit=500,
		ignore_permissions=True,
	)
	return [
		{
			"who": frappe.utils.get_fullname(row.user),
			"for": "organisation" if row.party == gate.WORKSPACE else "self",
			"version": row.version,
			"on": frappe.utils.format_datetime(row.accepted_on),
		}
		for row in rows
	]


@frappe.whitelist(methods=["GET"])
def of_module(module: str) -> dict:
	"""What one module adds to the agreements, for its Legal tab: everybody's
	to read, since the agreements are everybody's."""
	said = assemble.of_module(module)
	for one in said["documents"]:
		title = one["title"]
		one["title"] = _(title)
		for section in one["sections"]:
			heading = section["heading"]
			section["heading"] = _(heading)
	return said


@frappe.whitelist(methods=["GET"])
def trust(module: str = "") -> dict:
	"""Everything TrustCenter shows (docs/READY.md, mechanism 13), in the
	reader's language: what a module adds, its optional services and every
	other, each agreement with where the reader and the workspace stand on it
	and the change coming to it, every company that receives data and whether
	this workspace uses it, what is kept and how to leave, and every change
	published."""
	from . import registry, services, switchovers
	from .documents import CHANGES, DOCUMENTS

	assemble._load()
	said = overview()
	for one in said["documents"]:
		rendered = assemble.render(one["key"])
		one["html"] = re.sub(r'<p class="summary">.*?</p>', "", rendered["html"].split("</h1>", 1)[-1], count=1)
		one["effective"] = gate.effective(one["key"])
		one["history"] = history(one["key"])
		change = next((c for c in reversed(CHANGES) if c["document"] == one["key"]), None)
		one["change"] = change["says"] if change and gate.effective(one["key"]) else None
	standing = services.standing()
	used = {one["key"]: one for one in standing}
	companies = [
		{
			"name": row["name"],
			"url": row["url"],
			"safeguard": row["safeguard"],
			"uses": [
				{
					"module": use["module"],
					"purpose": use["purpose"],
					"data": use["data"],
					"where": use["where"],
					"service": used[use["service"]]["title"] if use["service"] else None,
					"used": not use["service"] or bool(used[use["service"]]["on"]),
					"starts": frappe.utils.formatdate(switchovers.effective(use.get("starts"))) if use.get("starts") else None,
				}
				for use in row["uses"]
			],
		}
		for row in registry.subprocessor_rows()
	]

	def bodies(document: str, section: str, keys: tuple = ()) -> list[str]:
		return [one["body"] for one in registry.clauses_for(document, section) if not keys or one["key"] in keys]

	today = frappe.utils.today()
	return {
		**said,
		"module": of_module(module) if module else None,
		"services": standing,
		"companies": companies,
		"data": {
			"kept": bodies("privacy", "keeping"),
			"yours": bodies("privacy", "rights", ("privacy-requests",)),
			"leaving": bodies("terms", "content", ("export",)) + bodies("terms", "suspension", ("switching",)),
		},
		"changes": [
			{
				"document": one["document"],
				"title": _titled(one["document"]),
				"revision": one["revision"],
				"published": frappe.utils.formatdate(one["published"]),
				"effective": frappe.utils.formatdate(one["effective"]),
				"coming": one["effective"] > today,
				"says": one["says"],
			}
			for one in reversed(CHANGES)
		],
	}


def _titled(key: str) -> str:
	from .documents import DOCUMENTS

	title = DOCUMENTS[key]["title"]
	return _(title)
