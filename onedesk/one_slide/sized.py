"""A picture on a slide at the size a screen shows it, and no larger (D2 of
one_display/SCRATCHPAD.md). A screen asks for a picture with the longest
edge it can show (`api.shown`'s `edge`). A picture longer than that is
served as a copy made once in the background, beside the original and at
high quality; the original is kept, and is what is served until the copy
is made, and always to the editor. A picture never grows."""

import io
import os

import frappe

from onedesk.one_cloud import store

QUALITY = 92
MADE = "one_slide:sized:{0}:{1}"
# the original is already no larger than the edge
SAME = "same"


def bucket(pixels: int) -> int:
	"""The copy size that covers `pixels` along the longest edge. Pure."""
	return next((edge for edge in store.SCREEN_EDGES if edge >= pixels), store.SCREEN_EDGES[-1])


def served(file_id: str, edge) -> dict | None:
	"""The copy to serve for a screen showing at most `edge` along its longest
	side, as {"key"} in R2 or {"path"} on disk; None serves the original."""
	edge = frappe.utils.cint(edge)
	if edge not in store.SCREEN_EDGES:
		return None
	held = frappe.cache.get_value(MADE.format(file_id, edge))
	if held is None:
		frappe.enqueue(
			"onedesk.one_slide.sized.make", file_id=file_id, edge=edge, queue="long",
			job_id=f"one_slide_sized:{file_id}:{edge}", deduplicate=True,
		)
		return None
	return None if held == SAME else held


def make(file_id: str, edge: int) -> None:
	"""The copy, made once: the picture turned upright as its camera meant,
	shrunk to `edge` along its longest side, saved as the kind it was."""
	from PIL import Image, ImageOps

	doc = frappe.get_doc("File", file_id)
	name = store.key_of(doc.file_url) if store.is_stored(doc.file_url) else doc.get_full_path()
	if not store.screen_copies(name):
		frappe.cache.set_value(MADE.format(file_id, edge), SAME)
		return
	content = store.get(name) if store.is_stored(doc.file_url) else open(name, "rb").read()
	picture = Image.open(io.BytesIO(content))
	kind = picture.format or "PNG"
	if max(picture.size) <= edge or getattr(picture, "is_animated", False):
		frappe.cache.set_value(MADE.format(file_id, edge), SAME)
		return
	picture = ImageOps.exif_transpose(picture)
	picture.thumbnail((edge, edge), Image.Resampling.LANCZOS)
	buffer = io.BytesIO()
	if kind == "JPEG":
		picture.convert("RGB").save(buffer, "JPEG", quality=QUALITY, subsampling=0, optimize=True, progressive=True)
	elif kind == "WEBP":
		picture.save(buffer, "WEBP", quality=QUALITY, method=6)
	else:
		picture.save(buffer, kind, optimize=True)
	copy = store.screen_copy(name, edge)
	if store.is_stored(doc.file_url):
		store.put(copy, buffer.getvalue())
		made = {"key": copy}
	else:
		with open(copy, "wb") as written:
			written.write(buffer.getvalue())
		made = {"path": os.path.relpath(copy, frappe.get_site_path())}
	frappe.cache.set_value(MADE.format(file_id, edge), made)
