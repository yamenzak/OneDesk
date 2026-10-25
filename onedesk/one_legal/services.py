"""The optional services (docs/READY.md, mechanism 13): what a module sends
out only once a workspace administrator turns it on and agrees to it. Off
by default, and off again once it sends somewhere new (README, Under the
hood)."""

import hashlib

import frappe
from frappe import _

from . import assemble, gate
from .registry import SERVICES, services_of

SWITCH = "one_service_{}"


def _declared(key: str) -> dict:
	assemble._load()
	if key not in SERVICES:
		frappe.throw(_("There is no such service."))
	return next(one for one in services_of() if one["key"] == key)


def version_of(key: str) -> str:
	"""`reach.words`, each eight hex characters. Pure apart from the registry."""
	one = _declared(key)
	reach = repr(sorted((c["name"], c["data"], c["where"]) for c in one["companies"]) + sorted(one["hosts"]))
	words = repr((one["title"], one["does"], one["sends"], one["off"]))
	return f"{_hash(reach)}.{_hash(words)}"


def _hash(text: str) -> str:
	return hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]


def document(key: str) -> str:
	return f"service:{key}"


def _accepted(key: str) -> str | None:
	return gate._accepted(document(key), gate.WORKSPACE)


def on(key: str) -> bool:
	"""Whether the workspace has a service on: switched on, and agreed to
	where it sends data now. Asked once per request."""
	known = getattr(frappe.local, "one_services", None)
	if known is None:
		known = frappe.local.one_services = {}
	if key not in known:
		known[key] = frappe.db.get_default(SWITCH.format(key)) == "1" and gate.agreed(
			_accepted(key), version_of(key)
		)
	return known[key]


def call(key: str, ask, *args, **kwargs):
	"""`ask(*args, **kwargs)` when the service is on, else None: the one
	way a module reaches a service's hosts (test_legal.py holds it)."""
	if not on(key):
		return None
	return ask(*args, **kwargs)


def standing(module: str | None = None) -> list[dict]:
	"""Each optional service, a module's or all: what it does and sends,
	to whom, what happens while it is off, whether it is on, and who agreed
	to it and when."""
	assemble._load()
	out = []
	for one in services_of(module):
		row = frappe.get_all(
			"Legal Acceptance",
			filters={"document": document(one["key"]), "party": gate.WORKSPACE},
			fields=["version", "user", "accepted_on"],
			order_by="creation desc",
			limit=1,
			ignore_permissions=True,
		)
		now = version_of(one["key"])
		switched = frappe.db.get_default(SWITCH.format(one["key"])) == "1"
		agreed = bool(row) and gate.agreed(row[0].version, now)
		out.append(
			{
				"key": one["key"],
				"module": one["module"],
				"title": one["title"],
				"does": one["does"],
				"sends": one["sends"],
				"off": one["off"],
				"companies": [{"name": c["name"], "where": c["where"], "data": c["data"]} for c in one["companies"]],
				"on": int(switched and agreed),
				"asks_again": int(switched and not agreed),
				"agreed_by": frappe.utils.get_fullname(row[0].user) if agreed else None,
				"agreed_on": frappe.utils.format_datetime(row[0].accepted_on) if agreed else None,
				"version": now,
			}
		)
	return out


@frappe.whitelist(methods=["POST"])
def switch(key: str, on: int) -> list[dict]:
	"""Turn an optional service on, which agrees to it for the workspace, or
	off, which stops what it sends. Only a workspace administrator binds the
	workspace (gate._may_bind)."""
	one = _declared(key)
	if not gate._may_bind():
		frappe.throw(_("Only a workspace administrator can turn this on or off."), frappe.PermissionError)
	_set(key, on)
	return standing(one["module"])


def _set(key: str, on: int) -> None:
	"""Turn a service on, agreeing to it as the reader, or off. Asked by
	`switch` and by the setup wizard, whose reader is setting the workspace
	up."""
	if int(on):
		version = version_of(key)
		if not gate.agreed(_accepted(key), version):
			frappe.get_doc(
				{
					"doctype": "Legal Acceptance",
					"document": document(key),
					"version": version,
					"party": gate.WORKSPACE,
					"user": frappe.session.user,
					"accepted_on": frappe.utils.now_datetime(),
					"address": (getattr(frappe.local, "request_ip", None) or "")[:140],
					"agent": gate._agent(),
				}
			).insert(ignore_permissions=True)
	frappe.db.set_default(SWITCH.format(key), "1" if int(on) else "0")
	frappe.local.one_services = {}


def for_wizard() -> dict | None:
	"""The setup wizard's slide for the optional services: a switch each,
	all off, which agrees to one for the workspace when turned on."""
	assemble._load()
	if not SERVICES:
		return None
	return {
		"name": "one_services",
		"title": _("Optional Services"),
		"help": _("Each sends something to another company, and stays off unless you turn it on. Turning one on agrees to it for your whole workspace."),
		"fields": [
			{"fieldtype": "Check", "fieldname": f"one_service_{one['key']}", "label": one["title"], "description": one["sends"], "default": 0}
			for one in SERVICES.values()
		],
	}


def from_wizard(args: dict) -> None:
	"""A setup wizard task: each service turned on there, agreed to."""
	for key in SERVICES:
		if (args or {}).get(f"one_service_{key}"):
			_set(key, 1)
