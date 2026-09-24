"""The page a link opens: /s/<token>, for somebody with no account.

It asks for what the link needs (a password, or an invited address and the
code sent to it), then shows the file or the folder. Everything a guest may
do goes through one_storage/links.py, which decides; this only draws.
"""

from urllib.parse import quote, unquote

import frappe
from frappe import _

from onedesk.one_storage import links
from onedesk.one_storage import namespace as ns

no_cache = 1

SAID = {
	"wrong": lambda: _("That password is not right."),
	"wrong_code": lambda: _("That code is not right, or it has run out."),
	"sent": lambda: _("If that address was invited, a code is on its way to it."),
}


def get_context(context):
	context.no_cache = 1
	token = frappe.form_dict.get("token")
	context.token = token
	link = links.live(token)
	context.link = link
	if not link:
		context.gone = True
		return context
	said = frappe.form_dict.get("said") or ""
	context.said = SAID[said]() if said in SAID else None
	context.said_wrong = said.startswith("wrong")
	if said.startswith("sent_"):
		count = int(said[5:] or 0) if said[5:].isdigit() else 0
		context.said = _("Sent {0} files. Thank you.").format(count) if count != 1 else _("Sent 1 file. Thank you.")
	context.by = frappe.utils.get_fullname(link.owner)
	who = links.opened_as(link)
	if who is None:
		context.ask = links.needs(link)
		context.asked_email = unquote(frappe.request.cookies.get("oc_email") or "") if said == "sent" else None
		return context
	links.seen(link)
	here = links._within(link, frappe.form_dict.get("in"))
	context.here = here
	context.here_urls = _urls(token, here.name)
	if here.is_folder:
		context.items = [{**one, **_urls(token, one["id"])} for one in links.contents(link, here.name)]
		context.trail = _trail(link, here)
	return context


def _urls(token: str, name: str) -> dict:
	item = f"token={quote(token)}&item={quote(name, safe='')}"
	return {
		"open": f"/api/method/onedesk.one_storage.links.get?{item}",
		"save": f"/api/method/onedesk.one_storage.links.get?{item}&download=1",
		"into": f"/s/{quote(token)}?in={quote(name, safe='')}",
	}


def _trail(link, here) -> list:
	"""From the shared folder down to where the guest is."""
	path = [here.name]
	for name in ns.chain(here.folder):
		path.append(name)
		if name == link.file:
			break
	if here.name == link.file:
		path = [here.name]
	rows = {one.name: one.file_name for one in frappe.get_all("File", filters={"name": ["in", path]}, fields=["name", "file_name"])}
	return [{"id": name, "name": rows.get(name, name)} for name in reversed(path)]
