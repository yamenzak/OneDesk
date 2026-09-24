"""Sharing inside the team: people, and what they may do.

A share is Frappe's own DocShare on a File: read to view, read and write to
edit. `namespace.may` reads it for the item and every folder above it, so a
folder shared is everything in it shared, including what is put there later,
and the File's own permission (which already honours DocShare) agrees with us
for a file shared on its own.

**Whoever may change a thing may share it**, the way it works in every
drive people know: its owner, a Workspace Administrator, or somebody it was
shared with to edit. Only staff can be given anything here; a customer or a
supplier gets a link (stage 5), not a seat.

**A record's file is shared by sharing the record.** Its permission is the
record's, and a second, file-only door beside it would drift from it.
"""

from urllib.parse import quote

import frappe
import frappe.share
from frappe import _
from frappe.utils import get_fullname

from onedesk.one_storage import api
from onedesk.one_storage import namespace as ns


def _shareable(node_id: str) -> dict:
	item = api._item(node_id)
	if item.attached_to_doctype and item.attached_to_name and not item.is_folder:
		frappe.throw(_("{0} belongs to {1} {2}. Share the record instead.").format(
			item.file_name, _(item.attached_to_doctype), item.attached_to_name
		))
	if item.one_home_of:
		frappe.throw(_("Share the folders in My Files, not My Files itself."))
	if not ns.may(item, "write"):
		frappe.throw(_("You may not share {0}.").format(item.file_name), frappe.PermissionError)
	return item


@frappe.whitelist()
@frappe.read_only()
def people(node: str) -> dict:
	"""Who has this, and whether the reader may change that."""
	item = api._item(node)
	if not ns.may(item):
		frappe.throw(_("That is no longer here."), frappe.DoesNotExistError)
	rows = frappe.get_all(
		"DocShare",
		filters={"share_doctype": "File", "share_name": item.name, "everyone": 0},
		fields=["user", "write"],
		order_by="creation asc",
	)
	# What reaches it from a folder above, for the reader to see where it
	# comes from; it is changed on that folder.
	above = frappe.get_all(
		"DocShare",
		filters={"share_doctype": "File", "share_name": ["in", ns.chain(item.folder)] or [""], "everyone": 0},
		fields=["user", "write", "share_name"],
	)
	return {
		"owner": {"user": item.owner, "name": get_fullname(item.owner)},
		"can_share": _may_share(item),
		"people": [{"user": one.user, "name": get_fullname(one.user), "edit": bool(one.write)} for one in rows],
		"inherited": [
			{
				"user": one.user,
				"name": get_fullname(one.user),
				"edit": bool(one.write),
				"from": frappe.db.get_value("File", one.share_name, "file_name"),
			}
			for one in above
			if one.user not in {row.user for row in rows}
		],
	}


def _may_share(item: dict) -> bool:
	if item.one_home_of or (item.attached_to_doctype and item.attached_to_name and not item.is_folder):
		return False
	return ns.may(item, "write")


@frappe.whitelist(methods=["POST"])
def share(nodes: str | list, users: str | list, edit: int = 0) -> int:
	"""Give `users` view (or edit) on each node, and tell them."""
	nodes = frappe.parse_json(nodes) if isinstance(nodes, str) else nodes
	users = frappe.parse_json(users) if isinstance(users, str) else users
	staff = set(
		frappe.get_all(
			"User", filters={"name": ["in", users], "enabled": 1, "user_type": "System User"}, pluck="name"
		)
	)
	refused = [user for user in users if user not in staff]
	if refused:
		frappe.throw(_("Only people on the team can be given a file here: {0}.").format(", ".join(refused)))
	given = 0
	for node_id in nodes:
		item = _shareable(node_id)
		for user in staff - {item.owner, "Administrator"}:
			frappe.share.add_docshare(
				"File",
				item.name,
				user,
				read=1,
				write=int(edit),
				share=int(edit),
				flags={"ignore_share_permission": True},
			)
			_tell(user, item)
			given += 1
	ns.forget()
	return given


@frappe.whitelist(methods=["POST"])
def unshare(node: str, user: str) -> None:
	"""Take a person off a file or folder. Anybody may take themselves off."""
	item = api._item(node)
	if user != frappe.session.user:
		_shareable(node)
	frappe.share.remove("File", item.name, user, flags={"ignore_permissions": True})
	ns.forget()


@frappe.whitelist(methods=["POST"])
def set_edit(node: str, user: str, edit: int = 0) -> None:
	item = _shareable(node)
	if not frappe.db.exists("DocShare", {"share_doctype": "File", "share_name": item.name, "user": user}):
		frappe.throw(_("{0} does not have {1}.").format(get_fullname(user), item.file_name))
	frappe.share.add_docshare(
		"File", item.name, user, read=1, write=int(edit), share=int(edit), flags={"ignore_share_permission": True}
	)
	ns.forget()


def _tell(user: str, item: dict) -> None:
	"""A notification that opens the explorer on it, not File's own form."""
	from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification

	# A folder opens on itself; a file opens where the reader can see it.
	node = item.name if item.is_folder else ns.SHARED
	enqueue_create_notification(
		user,
		{
			"type": "Share",
			"document_type": "File",
			"document_name": item.name,
			"subject": _("{0} shared {1} with you").format(
				frappe.bold(get_fullname(frappe.session.user)), frappe.bold(item.file_name)
			),
			"from_user": frappe.session.user,
			"link": f"/desk/onecloud?node={quote(node, safe='')}",
		},
	)
