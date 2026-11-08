"""PDF tools in OneCloud: PDFs and pictures put together into one PDF, in
the order they were chosen, made here with pypdf and Pillow (both frappe's
own), so nothing leaves the site."""

import io

import frappe
from frappe import _
from PIL import Image, ImageOps
from pypdf import PdfReader, PdfWriter

from onedesk.one_storage import api, upload

PICTURES = {"png", "jpg", "jpeg", "webp", "gif", "bmp", "tif", "tiff"}
MOST_FILES = 100
MOST_BYTES = 200 * 1024 * 1024


def kind_of(name: str) -> str | None:
	"""'pdf', 'picture' or None, by a file's extension. Pure."""
	extension = (name or "").rsplit(".", 1)[-1].lower() if "." in (name or "") else ""
	if extension == "pdf":
		return "pdf"
	return "picture" if extension in PICTURES else None


def picture_page(content: bytes) -> bytes:
	"""A picture as a one-page PDF, turned the way the camera held it, at
	its own size (96 dots to the inch when it doesn't say). Pure."""
	picture = ImageOps.exif_transpose(Image.open(io.BytesIO(content)))
	if picture.mode in ("RGBA", "LA", "P"):
		picture = picture.convert("RGBA")
		paper = Image.new("RGB", picture.size, "white")
		paper.paste(picture, mask=picture.split()[-1])
		picture = paper
	elif picture.mode != "RGB":
		picture = picture.convert("RGB")
	dpi = picture.info.get("dpi", (96, 96))[0] or 96
	out = io.BytesIO()
	picture.save(out, format="PDF", resolution=float(dpi))
	return out.getvalue()


class Unreadable(Exception):
	"""A part that is not what its name says, or is locked with a password."""

	def __init__(self, name: str, locked: bool = False):
		super().__init__(name)
		self.name, self.locked = name, locked


def joined(parts: list[tuple[str, bytes, str]]) -> bytes:
	"""(kind, bytes, name) as one PDF, in order; Unreadable names the part
	that could not be read. Pure."""
	writer = PdfWriter()
	for kind, content, name in parts:
		try:
			reader = PdfReader(io.BytesIO(picture_page(content) if kind == "picture" else content))
			locked = reader.is_encrypted
			pages = [] if locked else list(reader.pages)
		except Exception as error:
			raise Unreadable(name) from error
		if locked:
			raise Unreadable(name, locked=True)
		for page in pages:
			writer.add_page(page)
	out = io.BytesIO()
	writer.write(out)
	return out.getvalue()


def _name(name: str | None, first: str) -> str:
	name = api._clean(name) or api._clean(first.rsplit(".", 1)[0]) or _("Combined")
	return name if name.lower().endswith(".pdf") else f"{name}.pdf"


@frappe.whitelist(methods=["POST"])
def combine(nodes: str | list, target: str, name: str | None = None) -> dict:
	"""PDFs and pictures, in the order given, made into one PDF in `target`.
	Each is read with the reader's own rights, and the new file is theirs."""
	nodes = frappe.parse_json(nodes) if isinstance(nodes, str) else nodes
	if not nodes:
		frappe.throw(_("Choose files to combine."))
	if len(nodes) > MOST_FILES:
		frappe.throw(_("Combine at most {0} files at once.").format(MOST_FILES))
	parts, size = [], 0
	for node in nodes:
		item = api._item(node)
		api._need(item, "read")
		kind = None if item.is_folder else kind_of(item.file_name)
		if not kind:
			frappe.throw(_("{0} is not a PDF or a picture.").format(item.file_name))
		size += item.file_size or 0
		if size > MOST_BYTES:
			frappe.throw(_("These files are over {0} MB together.").format(MOST_BYTES // 1024 // 1024))
		parts.append((kind, api._content(item), item.file_name))
	try:
		content = joined(parts)
	except Unreadable as error:
		if error.locked:
			frappe.throw(_("{0} is locked with a password.").format(error.name))
		frappe.throw(_("Could not read {0}.").format(error.name))
	return upload._place(target, None, {"file_name": _name(name, parts[0][2]), "content": content})
