"""Telling people that One's agreements and policies are changing
(trust_center/notifications.py)."""

import frappe

from onedesk.one import notify


def agreements_changed(titles: list[str], effective: str) -> None:
	"""A workspace agreement's new revision, told to every administrator, and
	always mailed: it takes effect on `effective`, at least thirty days on,
	and the Data Processing Addendum gives until then to object to a new
	subprocessor, which assumes they were told."""
	from onedesk.one.account import _administrators

	people = _administrators()
	if people:
		notify.notify(
			"Agreements Changed",
			people,
			link="/desk/legal?at=changes",
			sender="Administrator",
			documents=", ".join(titles),
			effective=frappe.utils.formatdate(effective),
		)


def policies_changed(titles: list[str], effective: str) -> None:
	"""A new revision of what each person agreed to themselves, the Privacy
	Policy say: told to everybody in the workspace, who is not asked again."""
	people = frappe.get_all("User", filters={"enabled": 1, "user_type": "System User", "name": ["not in", ["Administrator", "Guest"]]}, pluck="name")
	if people:
		notify.notify(
			"Policies Changed",
			people,
			link="/desk/legal?at=changes",
			sender="Administrator",
			documents=", ".join(titles),
			effective=frappe.utils.formatdate(effective),
		)
