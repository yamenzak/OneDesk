"""Telling people about files, shares, links and file requests
(notifications/one_storage/)."""

from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import get_fullname

from onedesk.one import notify


def shared(user: str, item: dict) -> None:
	"""A notification that opens the explorer on it, not File's own form."""
	from onedesk.one_storage import namespace as ns

	node = item.name if item.is_folder else ns.SHARED
	notify.notify(
		"Shared With You",
		user,
		record=("File", item.name),
		link=f"/desk/onecloud?node={quote(node, safe='')}",
		who=get_fullname(frappe.session.user),
		file=item.file_name,
	)


def added_to_library(user: str, item: dict) -> None:
	"""Somebody else was made a member of a library."""
	if user == frappe.session.user:
		return
	notify.notify(
		"Added to a Library",
		user,
		record=("File", item.name),
		link=f"/desk/onecloud?node={quote(item.name, safe='')}",
		who=get_fullname(frappe.session.user),
		library=item.file_name,
	)


def link_shared(link, emails: list, token: str) -> None:
	"""Each invited address is mailed the link."""
	from onedesk.one_storage.links import url_of

	who = get_fullname(frappe.session.user)
	for email in emails:
		notify.mail("Link Shared", email, now=False, who=who, file=link.file_name, link=url_of(token))


def code_asked(link, email: str, code: str) -> None:
	"""An invited address asked for the code that opens a link."""
	notify.mail("Link Code", email, delayed=False, file=link.file_name, code=code)


def arrived_through_link(link, into: dict, names: list) -> None:
	"""A link's owner hears of the files a guest sent through it."""
	notify.notify(
		"Arrived Through a Link" if len(names) > 1 else "Arrived Through a Link, One File",
		link.owner,
		record=("File", into.name),
		link=f"/desk/onecloud?node={quote(into.name, safe='')}",
		count=len(names),
		file=names[0],
		folder=into.file_name,
	)


def files_requested(doc, tokens: dict) -> None:
	"""Each new person asked for files is mailed their own link."""
	from markupsafe import Markup, escape

	from onedesk.one_storage.file_requests import url_of

	who = get_fullname(doc.owner)
	note = Markup("<br><br>") + escape(doc.message) if doc.message else ""
	due = (
		Markup("<br><br>") + escape(_("Due {0}.").format(frappe.format(doc.due_date, "Date")))
		if doc.due_date
		else ""
	)
	for email, token in tokens.items():
		notify.mail(
			"File Request",
			email,
			now=False,
			who=who,
			request=doc.title,
			note=note,
			due=due,
			link=url_of(token),
		)


def reminded(doc, person, who: str) -> None:
	"""A person asked for files is reminded of the request."""
	from onedesk.one_storage.file_requests import url_of

	notify.mail(
		"File Request Reminder",
		person.email,
		now=False,
		who=who,
		request=doc.title,
		link=url_of(person.get_password("token")),
	)


def request_answered(doc, person, item, finished: bool) -> None:
	"""The owner hears of each item sent, and once when a person has sent all of them."""
	from onedesk.one_storage.file_requests import node_id

	notify.notify(
		"File Request Complete" if finished else "File Request Answered",
		doc.owner,
		record=("Cloud File Request", doc.name),
		link=f"/desk/onecloud?node={quote(node_id(doc.name), safe='')}",
		sender="Guest",
		who=person.email,
		request=doc.title,
		item=item.label,
	)


def made(user: str, item: dict, folder: str) -> None:
	"""What OneAI made in the background is in its folder. Sent as the
	workspace, since the bell does not tell a person of their own doing."""
	notify.notify(
		"File Ready",
		user,
		record=("File", item["id"]),
		link=f"/desk/onecloud?node={quote(folder, safe='')}&file={quote(item['id'], safe='')}",
		sender="Administrator",
		file=item["name"],
	)


def not_made(user: str, what: str, folder: str) -> None:
	"""OneAI could not make what was asked."""
	notify.notify(
		"File Not Made",
		user,
		link=f"/desk/onecloud?node={quote(folder, safe='')}",
		sender="Administrator",
		what=what,
	)


def oneos_closed(user: str, name: str, file: str) -> None:
	"""A file somebody had open in OneOS was closed without them closing it:
	idle, at the time limit, for want of credits or because OneOS stopped
	answering. Sent as the workspace, since nobody pressed anything."""
	folder = frappe.db.get_value("File", name, "folder")
	notify.notify(
		"Closed in OneOS",
		user,
		record=("File", name),
		link=f"/desk/onecloud?node={quote(folder or '@recent', safe='')}&file={quote(name, safe='')}",
		sender="Administrator",
		file=file,
	)


def deleted_while_open(users: list[str], item) -> None:
	"""A file somebody had open, in OneOS, on the drive or in an editor,
	went to the Recycle Bin. The link opens the Recycle Bin on it."""
	from onedesk.one_storage import namespace as ns

	notify.notify(
		"Deleted While Open",
		users,
		record=("File", item.name),
		link=f"/desk/onecloud?node={quote(ns.BIN, safe='')}&file={quote(item.name, safe='')}",
		who=get_fullname(frappe.session.user),
		file=item.file_name,
	)
