"""Private apps: Frappe apps made for one workspace, and how they join One.

An installed app whose package declares itself in a manifest.py
(registry/private.py) is one of One's apps, always on and never
uninstalled. It arrives by a code typed into Apps, which the control plane
turns into an Install App job (one_admin/private.py). The rest is in one/AGENTS.md under Under the hood, and docs/PRIVATE-APPS.md.
"""

from pathlib import Path

import frappe
from frappe import _

from onedesk.one import registry
from onedesk.one.registry import Invalid
from onedesk.one.registry import private as manifest

LEAVE = "one_allow_private_uninstall"


def names() -> list[str]:
	"""The installed apps that are private apps, in install order."""
	return [app for app in frappe.get_installed_apps() if _declared(app)]


def _declared(app: str):
	"""Its manifest, read without running it; None for an app that has none
	or one the registry would not hold."""
	try:
		return manifest.at(Path(frappe.get_app_path(app)))
	except (Invalid, OSError, ImportError):
		return None


def about(app: str) -> dict:
	"""A private app's title, sentence and icon, from its manifest.py."""
	card = manifest.card(_declared(app))
	line = card["said"]
	return {"name": app, "title": card["title"], "said": _(line) if line else "", "icon": card["icon"] or "package"}


def offered() -> list[dict]:
	"""The cards Apps shows for them: always on, and never to be turned off;
	one whose plan feature the workspace's plan lacks is not shown."""
	from onedesk.account_center import plan

	return [{**about(app), "on": True, "kept": True} for app in names() if app not in _planless(plan.held())]


def _planless(held) -> set:
	from onedesk.one.registry import features

	return set() if held is None else {app for app in names() if features.missing(_declared(app).plan, held)}


def unplanned(held) -> list[str]:
	"""The rail rows of the private apps whose manifest needs a plan feature
	`held` lacks, for `apps.unplanned`."""
	from frappe.desk.doctype.dock.dock import get_app_dock

	return [row.get("link_to") for app in sorted(_planless(held)) for row in get_app_dock(app)]


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
		frappe.throw(_("{0} can't be reached right now. Try again in a few minutes.").format(registry.name("one_admin")))
	except faults.Refused as refused:
		if refused.said == "ValidationError" and refused.detail:
			frappe.throw(refused.detail, title=_("Not Found"))
		if not account.configured():
			frappe.throw(_("This workspace isn't linked to {0}, so it can't add private apps.").format(registry.name("one_admin")))
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
