"""Who has agreed to what, and who may not carry on until they do.

The workspace agrees to the contract once for everybody in it, and each person
agrees to what is about their own personal data. Only a first agreement stops
anybody: a later revision is notice, published ahead of the day it takes
effect (documents.CHANGES), and the version agreed to holds until then
(docs/READY.md, mechanism 13).
"""

import frappe
from frappe import _, _lt

from . import assemble
from .documents import DOCUMENTS, change_of

SHOWN = (
	_lt("Terms of Service"),
	_lt("The agreement between your organisation and Four Degree Labs for the use of One."),
	_lt("Acceptable Use Policy"),
	_lt("What One may not be used for, by your organisation or anyone who signs in."),
	_lt("Privacy Policy"),
	_lt("What we do with personal data: yours, and the personal data your organisation puts into One."),
	_lt("Cookie Policy"),
	_lt("What One stores on your device and why."),
	_lt("Data Processing Addendum"),
	_lt("How we handle personal data your organisation is responsible for, under the Terms of Service."),
	_lt("Subprocessors"),
	_lt("Every third party that receives customer data, what for, and where it is kept."),
	_lt("AI Addendum"),
	_lt("How OneAI works, which models run, and what happens to what you send it."),
	_lt("Open Source and Third-Party Notices"),
	_lt("The software One is built from, and the licences it carries."),
)

WORKSPACE = "Workspace"
USER = "User"

AUDIENCE = {"customer": (WORKSPACE,), "user": (USER,), "both": (WORKSPACE, USER)}


def keys_for(party: str) -> list[str]:
	"""The documents one party must accept, in the order they are shown."""
	return [key for key, one in DOCUMENTS.items() if one["audience"] and party in AUDIENCE[one["audience"]]]


def _may_bind() -> bool:
	"""Whether this person can accept on the workspace's behalf: one of its
	administrators, the people it has handed the workspace to. Deliberately not
	"anybody who can open the settings": binding the organisation to a contract
	is the one thing that should not be delegated by accident."""
	from onedesk.one import roles

	return roles.administers()


def revision(version: str | None) -> str | None:
	"""The part of a version that asks everybody again: `2` of `2.94da7c45`.
	Pure."""
	return version.split(".", 1)[0] if version else None


def agreed(was: str | None, now: str) -> bool:
	"""Whether what was accepted is what is published: the same revision. A
	new hash alone is a clarification or a typo (AGENTS.md). Pure."""
	return bool(was) and revision(was) == revision(now)


def effective(key: str) -> str | None:
	"""The day a document's current revision takes effect, while it is still
	to come: until then the revision agreed to holds."""
	change = change_of(key)
	if change and change["effective"] > frappe.utils.today():
		return change["effective"]
	return None


def _accepted(key: str, party: str, user: str | None = None) -> str | None:
	"""The version of `key` this party last accepted, if any."""
	filters = {"document": key, "party": party}
	if party == USER:
		filters["user"] = user or frappe.session.user
	rows = frappe.get_all(
		"Legal Acceptance",
		filters=filters,
		fields=["version"],
		order_by="creation desc",
		limit=1,
		ignore_permissions=True,
	)
	return rows[0]["version"] if rows else None


def workspace_behind() -> bool:
	"""Whether the workspace owes an agreement it has not given."""
	return any(not _accepted(key, WORKSPACE) for key in keys_for(WORKSPACE))


def standing(user: str | None = None) -> list[dict]:
	"""Every document that needs agreeing, and where this person stands on it."""
	user = user or frappe.session.user
	binds = _may_bind()
	rows = []

	for key, one in DOCUMENTS.items():
		if not one["audience"]:
			continue
		version = assemble.version_of(key)
		for party in AUDIENCE[one["audience"]]:
			if party == WORKSPACE and not binds:
				continue
			was = _accepted(key, party, user)
			rows.append(
				{
					"document": key,
					"title": one["title"],
					"summary": one["summary"],
					"party": party,
					"version": version,
					"accepted": bool(was),
					"changed": bool(was) and not agreed(was, version),
					"effective": effective(key),
					"previously": was,
				}
			)
	return rows


@frappe.whitelist(methods=["GET"])
def outstanding() -> dict:
	"""What this person has to agree to before carrying on.

	`blocking` is what they can do something about. `waiting` is what the
	workspace still owes and they cannot sign — an invited user cannot accept
	the Terms of Service, and should be told that rather than shown a button
	that will not work.
	"""
	rows = standing()
	blocking = [one for one in rows if not one["accepted"]]
	waiting = []

	if not _may_bind():
		for key in keys_for(WORKSPACE):
			if not _accepted(key, WORKSPACE):
				waiting.append({"document": key, "title": DOCUMENTS[key]["title"]})

	return {
		"blocking": blocking,
		"changed": [one for one in rows if one["changed"]],
		"waiting": waiting,
		"may_bind": _may_bind(),
		"ok": not blocking and not waiting,
	}


def _agent() -> str:
	"""The browser that accepted, when there is one.

	`frappe.get_request_header` reaches for a request object that is not bound
	outside one, and raises rather than returning nothing. Accepting is not
	only something a browser does — the dev fixture agrees on behalf of both
	its users, and a console or a migration may too — so the absence of a
	request is a blank field, not a failure.
	"""
	if not getattr(frappe.local, "request", None):
		return ""
	return (frappe.get_request_header("User-Agent") or "")[:500]


def record(key: str, party: str, user: str | None = None) -> dict:
	"""Write one acceptance, and the version's text if it is new here.

	`ignore_permissions` because accepting is the one write a person makes
	before they have been let in, and the row is about them.
	"""
	if key not in DOCUMENTS or not DOCUMENTS[key]["audience"]:
		frappe.throw(_("There is no such document to agree to."))
	if party not in (WORKSPACE, USER):
		frappe.throw(_("There is no such party."))
	if party == WORKSPACE and not _may_bind():
		frappe.throw(
			_("Your role doesn't allow agreeing for the organisation."),
			frappe.PermissionError,
		)

	rendered = assemble.render(key)
	version = rendered["version"]
	stored = f"{key}-{version}"

	if not frappe.db.exists("Legal Document Version", stored):
		frappe.get_doc(
			{
				"doctype": "Legal Document Version",
				"document": key,
				"title": rendered["title"],
				"version": version,
				"revision": rendered["revision"],
				"audience": rendered["audience"],
				"html": rendered["html"],
				"text": assemble.text_of(key),
			}
		).insert(ignore_permissions=True)

	row = frappe.get_doc(
		{
			"doctype": "Legal Acceptance",
			"document": key,
			"version": version,
			"stored_version": stored,
			"party": party,
			"user": user or frappe.session.user,
			"accepted_on": frappe.utils.now_datetime(),
			"address": (getattr(frappe.local, "request_ip", None) or "")[:140],
			"agent": _agent(),
		}
	).insert(ignore_permissions=True)

	return {"document": key, "party": party, "version": version, "name": row.name}


@frappe.whitelist(methods=["POST"])
def accept(documents: str | list) -> dict:
	"""Agree to a list of documents, as whichever party each one needs.

	The client sends what it was shown. Anything already accepted at this
	version is skipped rather than refused, because two tabs open at the same
	dialog is a thing that happens.
	"""
	wanted = frappe.parse_json(documents) if isinstance(documents, str) else documents
	if not isinstance(wanted, list):
		frappe.throw(_("Send the list of documents you are agreeing to."))

	done = []
	for key in wanted:
		one = DOCUMENTS.get(key)
		if not one or not one["audience"]:
			continue
		for party in AUDIENCE[one["audience"]]:
			if party == WORKSPACE and not _may_bind():
				continue
			if agreed(_accepted(key, party), assemble.version_of(key)):
				continue
			done.append(record(key, party))

	return {"accepted": done, **outstanding()}


def require(where: str = "") -> None:
	"""Refuse to go on while something is outstanding.

	Called from the paths where carrying on would be carrying on *under* an
	agreement nobody has made: creating a workspace, enabling a space. Not from
	every request — the shell asks once when it boots and puts the dialog up,
	and a check on every read would be a check on every read.
	"""
	answer = outstanding()
	if answer["ok"]:
		return
	said = _("This workspace has agreements outstanding. Agree to them, then try again.")
	frappe.throw(said + (f" ({where})" if where else ""), frappe.PermissionError)


def told_of_changes() -> None:
	"""after_migrate: a document at a new revision, told once per revision:
	the workspace's agreements to every administrator, by mail too, once the
	workspace has agreed to an earlier one; a person's own to everybody in the
	workspace. Nobody is stopped; the version agreed to holds until the day
	the new one takes effect."""
	from onedesk.trust_center import tell

	for party, told_by in ((WORKSPACE, tell.agreements_changed), (USER, tell.policies_changed)):
		titles, days = [], []
		for key in keys_for(party):
			now = revision(assemble.version_of(key))
			told = f"trust_center_told_{party.lower()}_{key}"
			if frappe.db.get_default(told) == now:
				continue
			if party == WORKSPACE:
				was = _accepted(key, WORKSPACE)
				if not was or revision(was) == now:
					continue
			elif not change_of(key):
				continue
			frappe.db.set_default(told, now)
			titles.append(str(DOCUMENTS[key]["title"]))
			days.append((change_of(key) or {}).get("effective") or frappe.utils.today())
		if titles:
			told_by(titles, min(days))
