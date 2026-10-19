"""Private apps: Frappe apps made for one workspace, and how they join One.

An installed app whose hooks.py says `one_private_app` is one of One's apps,
always on and never uninstalled. It arrives by a code typed into Apps, which
the control plane turns into an Install App job (one_admin/private.py). The
rest is in one/README.md under Under the hood, and docs/PRIVATE-APPS.md.
"""

import frappe
from frappe import _

HOOK = "one_private_app"

LEAVE = "one_allow_private_uninstall"


def names() -> list[str]:
	"""The installed apps that are private apps, in install order."""
	return [app for app in frappe.get_installed_apps() if _said(app)]


def _said(app: str) -> dict:
	try:
		said = frappe.get_hooks(HOOK, app_name=app) or {}
	except Exception:
		return {}
	return said if isinstance(said, dict) else {}


def about(app: str) -> dict:
	"""Its title, sentence and icon, from its hooks.py. A key given twice
	keeps the last. Pure over what the hook says."""
	said = {key: (value[-1] if isinstance(value, list) and value else value) for key, value in _said(app).items()}
	return {
		"name": app,
		"title": str(said.get("title") or app),
		"said": str(said.get("said") or ""),
		"icon": str(said.get("icon") or "package"),
	}


def offered() -> list[dict]:
	"""The cards Apps shows for them: always on, and never to be turned off."""
	return [{**about(app), "on": True, "kept": True} for app in names()]


def rail() -> set:
	"""What their Docks put on the rail, for `companions.layer`."""
	from frappe.desk.doctype.dock.dock import get_app_dock

	return {row.get("link_to") for app in names() for row in get_app_dock(app)}


def installed_now(app: str) -> None:
	"""`after_app_install`: a private app just installed joins the rail at
	once, and everybody hears Apps changed."""
	frappe.clear_cache()
	if app not in names():
		return
	from onedesk.one import companions

	companions.apply()
	frappe.publish_realtime("one_apps", after_commit=True)


def refuse_uninstall(app: str) -> None:
	"""`before_app_uninstall`: a private app installed stays. Only somebody
	with the server's site_config may lift that, for this one site."""
	if app in names() and not frappe.conf.get(LEAVE):
		frappe.throw(_("{0} is a private app, and a private app installed stays.").format(about(app)["title"]))


@frappe.whitelist(methods=["POST"])
def claim(code: str) -> dict:
	"""A code typed into Apps, handed to the control plane, which answers
	which app it opens and queues its install."""
	from onedesk.one import account, roles

	roles.require()
	code = (code or "").strip()
	if not code:
		frappe.throw(_("Type the code you were given."))
	from onedesk.one_admin import faults

	try:
		return account.ask("onedesk.one_admin.proxy.app_claim", code=code, by=frappe.session.user) or {}
	except faults.Again:
		frappe.throw(_("OneAdmin can't be reached right now. Try again in a few minutes."))
	except faults.Refused as refused:
		if refused.said == "ValidationError" and refused.detail:
			frappe.throw(refused.detail, title=_("Not Found"))
		if not account.configured():
			frappe.throw(_("This workspace isn't linked to OneAdmin, so it can't add private apps."))
		raise


def waiting() -> list[dict]:
	"""The private apps claimed and not yet here, with how far each has got.
	Nothing when the control plane can't be asked."""
	from onedesk.one import account

	try:
		said = account.ask("onedesk.one_admin.proxy.private_apps") or []
	except Exception:
		return []
	here = set(names())
	return [
		{"name": one.get("app"), "title": one.get("title"), "said": one.get("said") or "", "icon": one.get("icon") or "package", "state": one.get("state"), "on": False, "kept": True}
		for one in said
		if isinstance(one, dict) and one.get("app") not in here
	]
