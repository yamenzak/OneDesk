"""What this workspace's plan includes beyond its quotas, as its account last
said (one/account.py keeps `proxy.hello`'s `features` in Workspace Account).
A workspace whose account has not said, one with no account (a dev site, the
demo) or one whose account is older than features, is held to nothing: the
account refuses what its plan lacks either way. Read by the boot, the
optional services and the apps a plan opens."""

import json

import frappe

from onedesk.one.registry import features


def said(text: str | None) -> tuple[str, ...] | None:
	"""The ids an account's answer gave, or None when it gave none. Pure."""
	if not text:
		return None
	try:
		ids = json.loads(text)
	except ValueError:
		return None
	return tuple(one for one in ids if isinstance(one, str)) if isinstance(ids, list) else None


def held() -> tuple[str, ...] | None:
	"""The features the plan has, or None when nothing holds the workspace to any."""
	known = getattr(frappe.local, "one_plan_features", False)
	if known is False:
		known = frappe.local.one_plan_features = said(frappe.db.get_single_value("Workspace Account", "plan_features"))
	return known


def has(feature: str) -> bool:
	return not features.missing((feature,), held())


def boot(bootinfo) -> None:
	"""`frappe.boot.one_plan_features`: each declared feature and whether
	this workspace has it."""
	bootinfo["one_plan_features"] = {one: has(one) for one in features.IDS}
