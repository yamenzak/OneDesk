"""NotificationCenter (docs/READY.md, mechanism 15): each module's notification
types (its `notifications.py`, mechanism 8), the channels the workspace allows
for each, and what each person chooses. Everybody reads
and sets their own; only a workspace administrator sets the workspace's."""

import frappe
from frappe import _

from onedesk.one import notify, roles

# A person's own switches, over every type.
OWN = ("enabled", "enable_email_notifications", "enable_email_threads_on_assigned_document")

# What an administrator sets on a type: whether it is sent, and whether people
# may have it by email and by push. Whether a new person starts with a channel
# on is the module's to say (`email_default`, `push_default`), not theirs.
WORKSPACE = ("enabled", "one_allow_email", "one_allow_push")


def _settings():
	from frappe.desk.doctype.notification_settings.notification_settings import create_notification_settings

	if not frappe.db.exists("Notification Settings", frappe.session.user):
		create_notification_settings(frappe.session.user)
	return frappe.get_doc("Notification Settings", frappe.session.user)


def for_boot() -> list[str]:
	"""The modules NotificationCenter has a part for, for this reader: those
	whose types they can get, and every module with types for an
	administrator."""
	if roles.administers():
		apps = frappe.get_all("Notification Type", filters={"one_app": ["is", "set"], "one_rule": 0}, pluck="one_app", distinct=True)
	else:
		apps = {one["app"] for one in notify.choosable() if one["app"]}
	return sorted(apps)


def _why(one: dict) -> str:
	"""Why a channel can't be changed, when it can't."""
	if one.get("always"):
		return str(_("Always mailed, so you can answer it by replying."))
	said = []
	if not one["allowed"]:
		said.append(str(_("Not mailed in this workspace.")))
	if not one["push"]:
		said.append(str(_("Not pushed in this workspace.")))
	return " ".join(said)


@frappe.whitelist()
def yours(module: str | None = None) -> dict:
	"""The reader's own switches, and each type they can get, a module's or
	all, with whether it is mailed and pushed to them and whether they may
	change that."""
	doc = _settings()
	mailed = {row.notification_type for row in doc.email_notification_types}
	pushed = {row.notification_type for row in doc.get(notify.PUSH_FIELD) or []}
	return {
		"enabled": int(doc.enabled),
		"email": int(doc.enable_email_notifications),
		"threads": int(doc.enable_email_threads_on_assigned_document),
		"types": [
			{
				"name": one["name"],
				"label": one["label"],
				"about": one["about"],
				"app": one["app"],
				"oneai": int(bool(one.get("oneai"))),
				"email": int(one["always"] or (one["allowed"] and one["name"] in mailed)),
				"push": int(one["push"] and one["name"] in pushed),
				"may_email": int(one["allowed"]),
				"may_push": int(one["push"]),
				"why": _why(one),
			}
			for one in notify.choosable()
			if module is None or module == "" or one["app"] == module
		],
	}


@frappe.whitelist(methods=["POST"])
def choose(name: str, channel: str, on: int) -> None:
	"""Whether one type is mailed or pushed to the reader. A type that
	follows this one goes with it; a channel the workspace doesn't allow
	can't be chosen."""
	field = {"email": notify.EMAIL_FIELD, "push": notify.PUSH_FIELD}.get(channel)
	one = next((kind for kind in notify.choosable() if kind["name"] == name), None)
	if not field or not one or not one["allowed" if channel == "email" else "push"]:
		frappe.throw(_("That cannot be set."))
	names = {name, *one.get("twins", [])}
	doc = _settings()
	kept = [row.notification_type for row in doc.get(field) or [] if row.notification_type not in names]
	doc.set(field, [{"notification_type": kind} for kind in kept + (sorted(names) if frappe.utils.cint(on) else [])])
	doc.save(ignore_permissions=True)


@frappe.whitelist(methods=["POST"])
def switch(field: str, on: int) -> None:
	"""The reader's notifications, or their email of them, on or off."""
	if field not in OWN:
		frappe.throw(_("That cannot be set."))
	doc = _settings()
	doc.set(field, frappe.utils.cint(on))
	doc.save(ignore_permissions=True)


def _fixed(one: dict) -> bool:
	"""Whether Send This can't be turned off: a type One needs, or an email
	another app sends that has no switch of its own."""
	return bool(one.get("required") or (one.get("mailed_by") and not (one.get("switch") or one.get("notification"))))


@frappe.whitelist()
def workspace(module: str | None = None) -> list[dict]:
	"""Each type a module sends, or every type, with what the workspace set
	on it. For administrators."""
	roles.require()
	declared = notify.declared()
	filters = {"one_rule": 0}
	if module:
		filters["one_app"] = module
	rows = frappe.get_all("Notification Type", filters=filters, fields=["name", "one_app", "one_about", "one_outside", *WORKSPACE], order_by="one_app asc, name asc")
	out = []
	for row in rows:
		one = declared.get(row.name)
		if not one:
			continue
		out.append(
			{
				"name": row.name,
				"label": _(row.name),
				"about": _(row.one_about) if row.one_about else "",
				"app": row.one_app or "",
				"to": notify.to(row.name),
				"enabled": int(row.enabled),
				"fixed": int(_fixed(one)),
				"channels": int(not (row.one_outside or one.get("mailed_by"))),
				"always": int(bool(one.get("always_mailed"))),
				"words": int(not (one.get("mailed_by") or notify.upstream(one))),
				**{field: int(row.get(field) or 0) for field in WORKSPACE[1:]},
			}
		)
	return out


@frappe.whitelist(methods=["POST"])
def set_type(name: str, field: str, value: int) -> None:
	"""One setting of one type, as NotificationCenter › Words and Rules
	saves it."""
	roles.require()
	one = notify.declared().get(name)
	if field not in WORKSPACE or not one or (field == "enabled" and _fixed(one)):
		frappe.throw(_("That cannot be set."))
	doc = frappe.get_doc("Notification Type", name)
	doc.set(field, frappe.utils.cint(value))
	doc.save(ignore_permissions=True)
