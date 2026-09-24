"""Team libraries: a folder people are members of.

What SharePoint calls a document library and a team drive calls a shared
drive. It lives under Libraries rather than in anybody's My Files, so it does
not go when the person who made it does, and it is its members' rather than
everybody's the way Company is.

Membership is DocShare on the library's folder, like any share, with the role
in its bits: Reader (read), Member (write), Owner (write and share). So
`namespace.granted` already gives a member what is in the library, and
`namespace._library_may` adds the two things only a library has — that
belonging is the only way in, and that only an owner renames it or changes
who is in it.
"""

import frappe
import frappe.share
from frappe import _
from frappe.utils import get_fullname

from onedesk.one import roles
from onedesk.one_storage import api
from onedesk.one_storage import namespace as ns


def _manages(library: str) -> bool:
	user = frappe.session.user
	return user == "Administrator" or roles.ADMINISTRATOR in frappe.get_roles() or ns.role_in(library) == "Owner"


def _library(node: str) -> dict:
	item = api._item(node)
	if not item.one_library:
		frappe.throw(_("{0} is not a library.").format(item.file_name))
	return item


@frappe.whitelist(methods=["POST"])
def make(name: str) -> dict:
	"""A new library, with its maker as its owner."""
	if not ns._staff(frappe.session.user):
		frappe.throw(_("Only people on the team can make a library."), frappe.PermissionError)
	name = api._clean(name)
	if not name:
		frappe.throw(_("A library needs a name."))
	root = ns.library_root()
	doc = frappe.get_doc(
		{
			"doctype": "File",
			"is_folder": 1,
			"file_name": ns.unique_name(name, api._taken(root)),
			"folder": root,
			"one_library": 1,
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert()
	_give(doc.name, frappe.session.user, "Owner")
	ns.forget()
	return {**ns.node(ns.row(doc.name)), "role": "Owner"}


def _give(library: str, user: str, role: str) -> None:
	write, share = ns.ROLES[role]
	frappe.share.add_docshare(
		"File", library, user, read=1, write=write, share=share, flags={"ignore_share_permission": True}
	)


@frappe.whitelist()
@frappe.read_only()
def members(node: str) -> dict:
	item = _library(node)
	if not ns.may(item):
		frappe.throw(_("That is no longer here."), frappe.DoesNotExistError)
	rows = frappe.get_all(
		"DocShare",
		filters={"share_doctype": "File", "share_name": item.name, "everyone": 0},
		fields=["user", "write", "share"],
		order_by="creation asc",
	)
	return {
		"can_manage": _manages(item.name),
		"members": [
			{
				"user": one.user,
				"name": get_fullname(one.user),
				"role": "Owner" if one.share else "Member" if one.write else "Reader",
			}
			for one in rows
		],
	}


@frappe.whitelist(methods=["POST"])
def add(node: str, users: str | list, role: str = "Member") -> int:
	item = _library(node)
	if not _manages(item.name):
		frappe.throw(_("Only an owner of {0} can say who is in it.").format(item.file_name), frappe.PermissionError)
	if role not in ns.ROLES:
		frappe.throw(_("A member is a Reader, a Member or an Owner."))
	users = frappe.parse_json(users) if isinstance(users, str) else users
	staff = frappe.get_all(
		"User", filters={"name": ["in", users], "enabled": 1, "user_type": "System User"}, pluck="name"
	)
	for user in staff:
		_give(item.name, user, role)
		_tell(user, item)
	ns.forget()
	return len(staff)


@frappe.whitelist(methods=["POST"])
def remove(node: str, user: str) -> None:
	"""Take somebody out. Anybody may leave; a library keeps one owner."""
	item = _library(node)
	if user != frappe.session.user and not _manages(item.name):
		frappe.throw(_("Only an owner of {0} can say who is in it.").format(item.file_name), frappe.PermissionError)
	owners = frappe.get_all(
		"DocShare", filters={"share_doctype": "File", "share_name": item.name, "share": 1}, pluck="user"
	)
	if owners == [user]:
		frappe.throw(_("{0} is the last owner of {1}. Make somebody else an owner first.").format(
			get_fullname(user), item.file_name
		))
	frappe.share.remove("File", item.name, user, flags={"ignore_permissions": True})
	ns.forget()


def _tell(user: str, item: dict) -> None:
	from urllib.parse import quote

	from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification

	if user == frappe.session.user:
		return
	enqueue_create_notification(
		user,
		{
			"type": "Share",
			"document_type": "File",
			"document_name": item.name,
			"subject": _("{0} added you to the library {1}").format(
				frappe.bold(get_fullname(frappe.session.user)), frappe.bold(item.file_name)
			),
			"from_user": frappe.session.user,
			"link": f"/desk/onecloud?node={quote(item.name, safe='')}",
		},
	)
