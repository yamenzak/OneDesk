"""Files a browser can't open (Word, Excel, PowerPoint, OpenDocument and the
like), read as PDFs made in One's office containers through OneAdmin
(one_admin/office.py), when somebody asks: a preview kept for a day by the
file's content, or a PDF saved beside it."""

import base64

import frappe
from frappe import _

from onedesk.one_storage import api, upload

OFFICE = {
	"doc", "docx", "docm", "dot", "dotx", "odt", "ott", "rtf", "wpd", "wps", "pages",
	"xls", "xlsx", "xlsm", "xlsb", "ods", "ots", "numbers",
	"ppt", "pptx", "pps", "ppsx", "odp", "otp", "key",
	"odg", "vsd", "vsdx", "pub",
}
KEPT_FOR = 24 * 60 * 60
MOST_KEPT = 20 * 1024 * 1024


def converts(name: str) -> bool:
	"""Whether a file is one the office containers turn into a PDF. Pure."""
	return "." in (name or "") and name.rsplit(".", 1)[-1].lower() in OFFICE


def _pdf(item) -> bytes:
	if item.is_folder or not converts(item.file_name):
		frappe.throw(_("{0} can't be converted to PDF.").format(item.file_name))
	key = f"one_storage_office:{frappe.db.get_value('File', item.name, 'content_hash') or item.name}"
	held = frappe.cache.get_value(key)
	if held:
		return held
	from onedesk.one import account

	said = account.ask("onedesk.one_admin.proxy.office_convert", name=item.file_name, data=base64.b64encode(api._content(item)).decode(), reference=f"OneCloud {item.name}")
	made = base64.b64decode((said or {}).get("data") or "")
	if not made.startswith(b"%PDF"):
		frappe.throw(_("This file could not be converted."))
	if len(made) <= MOST_KEPT:
		frappe.cache.set_value(key, made, expires_in_sec=KEPT_FOR)
	return made


@frappe.whitelist()
def preview(node: str) -> None:
	"""The file as a PDF, to read in the viewer: made once a day per content,
	and billed in credits when it is made."""
	item = api._item(node)
	api._need(item, "read")
	frappe.local.response.filename = item.file_name.rsplit(".", 1)[0] + ".pdf"
	frappe.local.response.filecontent = _pdf(item)
	frappe.local.response.type = "binary"


@frappe.whitelist(methods=["POST"])
def to_pdf(node: str) -> dict:
	"""The file as a PDF saved beside it, in the same folder: the new node."""
	item = api._item(node)
	api._need(item, "read")
	if not item.folder:
		frappe.throw(_("{0} is not in a folder.").format(item.file_name))
	return upload._place(item.folder, None, {"file_name": item.file_name.rsplit(".", 1)[0] + ".pdf", "content": _pdf(item)})
