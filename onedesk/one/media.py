"""The pictures and clips in Help and What's New, written beside the page or
version that shows them and read from R2 under the hash of what each holds,
so a picture has the same address on dev and in production (docs/READY.md,
Pictures and clips). Until R2 has one, this site serves it (`picture`).
"""

import hashlib
import mimetypes
import re
from pathlib import Path
from urllib.parse import quote

import frappe
from frappe import _

from onedesk.one import ready

# R2's `one-docs` bucket, public on this domain (one_admin/setup.py
# `docs_media`). A site may name another in `one_media`.
DOMAIN = "media.4dl.app"
PREFIX = "docs"
KINDS = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif"}
PICTURE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")
# A clip plays for at most this long, and no file is larger than this
# (tests/guards/test_docs_media.py).
LONGEST_CLIP = 9.0
LARGEST = {".gif": 4 * 1024 * 1024}
LARGEST_PICTURE = 1024 * 1024

_hashes: dict[tuple[str, float], str] = {}


def key(path: Path) -> str:
	"""The file's name in R2: the hash of what it holds and its kind. Pure."""
	stamp = (str(path), path.stat().st_mtime)
	if stamp not in _hashes:
		_hashes[stamp] = hashlib.sha256(path.read_bytes()).hexdigest()[:24]
	return f"{PREFIX}/{_hashes[stamp]}{path.suffix.lower()}"


def base() -> str:
	return "https://" + (frappe.conf.get("one_media") or DOMAIN).strip("/").removeprefix("https://")


def files(module: str) -> list[Path]:
	"""Every picture and clip a module's Help and What's New show."""
	folder = ready.APP / ready.MODULES[module]["folder"] / "docs"
	return sorted(path for path in folder.rglob("*") if path.suffix.lower() in KINDS)


def every() -> list[Path]:
	return [path for module in ready.MODULES for path in files(module)]


def pictured(module: str, body: str, beside: Path) -> str:
	"""Markdown with each picture beside it drawn as an image at its R2
	address, carrying the address this site serves it from if R2 does not
	have it yet. A picture outside the module's docs, or not there, leaves
	its words."""
	folder = (ready.APP / ready.MODULES[module]["folder"] / "docs").resolve()

	def draw(found: re.Match) -> str:
		alt, named = found.group(1), found.group(2)
		path = (beside.parent / named).resolve()
		if not path.is_relative_to(folder) or not path.exists() or path.suffix.lower() not in KINDS:
			return alt
		held = path.relative_to(folder).as_posix()
		here = f"/api/method/onedesk.one.media.picture?module={quote(module)}&path={quote(held)}"
		said = frappe.utils.escape_html(alt)
		return (
			f'<img src="{base()}/{key(path)}" data-here="{here}" alt="{said}" title="{said}" loading="lazy"'
			f'{" data-clip=1" if path.suffix.lower() == ".gif" else ""}>'
		)

	return PICTURE.sub(draw, body)


@frappe.whitelist()
def picture(module: str, path: str):
	"""A picture of a module's Help from the repository, for when R2 does
	not have it yet."""
	if module not in ready.MODULES:
		frappe.throw(_("{0} has no help.").format(module))
	folder = (ready.APP / ready.MODULES[module]["folder"] / "docs").resolve()
	found = (folder / path).resolve()
	if not found.is_relative_to(folder) or not found.is_file() or found.suffix.lower() not in KINDS:
		raise frappe.DoesNotExistError
	frappe.local.response.filename = found.name
	frappe.local.response.filecontent = found.read_bytes()
	frappe.local.response.content_type = KINDS[found.suffix.lower()]
	frappe.local.response.display_content_as = "inline"
	frappe.local.response.type = "download"


def kind(path: Path) -> str:
	return KINDS.get(path.suffix.lower()) or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
