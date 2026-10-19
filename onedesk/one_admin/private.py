"""Apps made for some workspaces only, and the codes that give them.

The operator makes a code for one workspace (`new_code`); typed into Apps
there, `claim` queues an Install App job that installs the app on its site.
The rest is in one_admin/README.md under private.py, and docs/PRIVATE-APPS.md.
"""

import hashlib
import json
import secrets

import frappe
from frappe import _
from frappe.utils import now_datetime

from onedesk.one_admin import site

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

LENGTH = 12

KIND = "Install App"


def normal(code: str | None) -> str:
	"""A code as typed, without the dashes, spaces and case people add. Pure."""
	return "".join(ch for ch in (code or "").upper() if ch.isalnum())


def hashed(code: str | None) -> str:
	return hashlib.sha256(normal(code).encode()).hexdigest()


def spaced(raw: str) -> str:
	"""ABCD-EFGH-JKLM: easier to read out over the phone. Pure."""
	return "-".join(raw[at : at + 4] for at in range(0, len(raw), 4))


@frappe.whitelist(methods=["POST"])
def new_code(app: str, tenant: str) -> str:
	"""A new code for this workspace to claim the app with, shown once.

	A workspace already offered the app gets a new code in place of the old,
	which stops working. One that has claimed it needs no code.
	"""
	site.require_admin()
	frappe.only_for(site.OPERATOR)
	doc = frappe.get_doc("Private App", app)
	if not frappe.db.exists("Tenant", tenant):
		frappe.throw(_("There is no workspace {0}.").format(tenant))
	raw = "".join(secrets.choice(ALPHABET) for _ in range(LENGTH))
	row = next((one for one in doc.grants if one.tenant == tenant), None)
	if row and row.status != "Offered":
		frappe.throw(_("{0} has already claimed {1}.").format(tenant, doc.title))
	row = row or doc.append("grants", {"tenant": tenant})
	row.update({"code_hash": hashed(raw), "code_end": raw[-4:], "status": "Offered"})
	doc.save(ignore_permissions=True)
	return spaced(raw)


def claim(tenant: str, code: str, by: str | None = None) -> dict:
	"""The app this code opens for this workspace, queued to install.

	Typing a claimed code again answers how far it has got rather than queuing
	a second install. Every code that opens nothing gets the same answer.
	"""
	found = frappe.get_all(
		"Private App Grant",
		filters={"parenttype": "Private App", "tenant": tenant, "code_hash": hashed(code)},
		fields=["name", "parent", "status", "job"],
		limit=1,
	)
	if not normal(code) or not found or not frappe.db.get_value("Private App", found[0].parent, "enabled"):
		frappe.throw(_("That code doesn't open an app for this workspace."), title=_("Not Found"))
	row = found[0]
	if row.status == "Offered":
		from onedesk.one_admin import runner

		job = runner.start(tenant, KIND, payload={"app": row.parent, "grant": row.name})
		frappe.db.set_value(
			"Private App Grant",
			row.name,
			{"status": "Installing", "job": job, "claimed_on": now_datetime(), "claimed_by": (by or "")[:140]},
			update_modified=False,
		)
	return _shown(frappe.db.get_value("Private App Grant", row.name, ["name", "parent", "status", "job"], as_dict=True))


def mine(tenant: str) -> list[dict]:
	"""What this workspace has claimed, and how far each install has got."""
	return [
		_shown(row)
		for row in frappe.get_all(
			"Private App Grant",
			filters={"parenttype": "Private App", "tenant": tenant, "status": ["!=", "Offered"]},
			fields=["name", "parent", "status", "job"],
			order_by="claimed_on asc",
		)
	]


def state(status: str, job_status: str | None) -> str:
	"""Installing, Installed or Failed, as the workspace sees it. Pure."""
	if status == "Installed":
		return "Installed"
	if status == "Failed" or job_status == "Failed":
		return "Failed"
	return "Installing"


def _shown(row) -> dict:
	app = frappe.db.get_value("Private App", row.parent, ["app", "title", "said", "icon"], as_dict=True)
	job = frappe.db.get_value("Provisioning Job", row.job, "status") if row.job else None
	return {"app": app.app, "title": app.title, "said": app.said or "", "icon": app.icon or "", "state": state(row.status, job)}


def wanted(job) -> dict:
	"""The app and grant an Install App job is for."""
	return json.loads(job.payload or "{}") or {}


def installed(job) -> None:
	"""The job's last step: the grant says Installed."""
	grant = wanted(job).get("grant")
	if grant:
		frappe.db.set_value("Private App Grant", grant, "status", "Installed", update_modified=False)
