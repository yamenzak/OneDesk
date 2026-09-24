"""Frappe's File, reading its content back from R2.

Frappe reads a file's content by opening a path on disk; for a stored file
(one_storage/store.py) there is no path, so the three methods that go to the
disk go to R2 instead. Everything else is Frappe's own.
"""

import io
import os

import filetype
import frappe
from frappe import _
from frappe.core.doctype.file.file import FILE_ENCODING_OPTIONS, OLE_FILE_SIGNATURE, File

from onedesk.one_storage import store


class CloudFile(File):
	def exists_on_disk(self):
		"""A stored file exists wherever it is kept, which is how Frappe's
		de-duplication by content finds it."""
		if store.is_stored(self.file_url):
			return True
		return super().exists_on_disk()

	def get_content(self, encodings=None) -> bytes | str:
		if self.get("content") or not store.is_stored(self.file_url):
			return super().get_content(encodings)
		if self.is_folder:
			frappe.throw(_("Cannot get file contents of a Folder"))
		self._content = decoded(store.get(store.key_of(self.file_url)), encodings)
		return self._content

	def make_thumbnail(self, set_as_thumbnail=True, width=300, height=300, suffix="small", crop=False):
		"""Frappe makes thumbnails from the disk or the web; a stored image's
		is made from its bytes and stored beside it."""
		if not store.is_stored(self.file_url):
			return super().make_thumbnail(set_as_thumbnail, width, height, suffix, crop)
		from frappe.utils.image import Image, ImageOps

		try:
			image = Image.open(io.BytesIO(store.get(store.key_of(self.file_url))))
		except Exception:
			return None
		if crop:
			image = ImageOps.fit(image, (width, height), Image.Resampling.LANCZOS)
		else:
			image.thumbnail((width, height), Image.Resampling.LANCZOS)
		extension = (image.format or "png").lower()
		buffer = io.BytesIO()
		image.save(buffer, format=image.format or "PNG")
		base = os.path.splitext(store.key_of(self.file_url))[0]
		key = f"{base}_{suffix}.{extension}"
		store.put(key, buffer.getvalue())
		url = store.url_for(key)
		if set_as_thumbnail:
			self.thumbnail_url = url
		return url


def decoded(content: bytes, encodings=None) -> bytes | str:
	"""Text as text and anything else as bytes, the way Frappe's own
	get_content decides."""
	kind = filetype.guess(content)
	if kind or content.startswith(OLE_FILE_SIGNATURE):
		return content
	for encoding in encodings or FILE_ENCODING_OPTIONS:
		try:
			return content.decode(encoding)
		except UnicodeDecodeError:
			continue
	return content
