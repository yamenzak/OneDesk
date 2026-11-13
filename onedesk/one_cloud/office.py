"""Files a browser can't open (Word, Excel, PowerPoint, OpenDocument and the
like), read as PDFs made in One's office containers through OneAdmin
(one_admin/office.py), when somebody asks: a preview, made and billed once
for each version of the file and kept with it, or a PDF saved beside it."""

import base64
import os

import frappe
from frappe import _

from onedesk.one_cloud import api, upload

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
	version = frappe.db.get_value("File", item.name, "content_hash")
	key = f"one_cloud_office:{version or item.name}"
	held = frappe.cache.get_value(key) or _kept(item.name, version)
	if held:
		return held
	from onedesk.one import account

	said = account.ask("onedesk.one_admin.proxy.office_convert", name=item.file_name, data=base64.b64encode(api._content(item)).decode(), reference=f"OneCloud {item.name}")
	made = base64.b64decode((said or {}).get("data") or "")
	if not made.startswith(b"%PDF"):
		frappe.throw(_("This file could not be converted."))
	if len(made) <= MOST_KEPT:
		frappe.cache.set_value(key, made, expires_in_sec=KEPT_FOR)
	if version:
		_keep(item.name, version, made)
	return made


def preview_key(version: str) -> str:
	"""Where the preview of a version is kept, by the version's content. Pure."""
	return f"previews/{version}.pdf"


def _on_disk(version: str) -> str:
	return frappe.get_site_path("private", "onecloud-previews", f"{version}.pdf")


def _kept(file: str, version: str | None) -> bytes | None:
	"""The preview made for this version of the file, when there is one."""
	from onedesk.one_cloud import store

	if not version or frappe.db.get_value("File", file, "one_preview_of") != version:
		return None
	try:
		if store.enabled():
			return store.get(preview_key(version))
		with open(_on_disk(version), "rb") as held:
			return held.read()
	except Exception:
		return None


def _keep(file: str, version: str, made: bytes) -> None:
	from onedesk.one_cloud import store

	try:
		if store.enabled():
			store.put(preview_key(version), made)
		else:
			os.makedirs(os.path.dirname(_on_disk(version)), exist_ok=True)
			with open(_on_disk(version), "wb") as held:
				held.write(made)
	except Exception:
		frappe.log_error(title="Keeping an office preview")
		return
	frappe.db.set_value("File", file, "one_preview_of", version, update_modified=False)


@frappe.whitelist()
def preview(node: str) -> None:
	"""The file as a PDF, to read in the viewer: made once for each version,
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
