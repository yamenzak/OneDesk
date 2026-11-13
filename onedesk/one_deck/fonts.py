"""The workspace's fonts: the faces One ships as app assets, Arabic among
them, and the workspace's own, kept as Files in OneCloud › Fonts so their
bytes live where every other file's do (AGENTS.md, Fonts)."""

import json
import re
import struct
from typing import Annotated

import frappe
from frappe import _

FOLDER_NAME = "Fonts"
SERVICE = "google_fonts"
KINDS = {"ttf": "font/ttf", "otf": "font/otf", "woff": "font/woff", "woff2": "font/woff2"}
FORMATS = {"ttf": "truetype", "otf": "opentype", "woff": "woff", "woff2": "woff2"}
MOST = 8 * 1024 * 1024
CATALOGUE = "https://fonts.google.com/metadata/fonts"
SHEET = "https://fonts.googleapis.com/css2"
FILES = "https://fonts.gstatic.com/"

#: The faces every workspace has: those One ships (slide/fonts.css) and the
#: ones every computer has under that name, in the picker's groups.
SHIPPED = (
	*({"family": one, "group": "arabic"} for one in ("IBM Plex Sans Arabic", "Noto Naskh Arabic", "Noto Kufi Arabic", "Cairo", "Tajawal", "Almarai", "Amiri")),
	*({"family": one, "group": "sans"} for one in ("Inter", "Arial", "Helvetica", "Tahoma", "Trebuchet MS", "Verdana", "Lucida Sans Unicode")),
	*({"family": one, "group": "serif"} for one in ("Georgia", "Palatino Linotype", "Times New Roman")),
	*({"family": one, "group": "display"} for one in ("Anton", "Arial Black", "Impact", "Comic Sans MS")),
	*({"family": one, "group": "mono"} for one in ("Courier Prime", "Courier New", "Lucida Console")),
)

WEIGHTS = {
	"thin": 100, "hairline": 100, "extralight": 200, "ultralight": 200, "light": 300, "regular": 400, "normal": 400,
	"book": 400, "medium": 500, "semibold": 600, "demibold": 600, "bold": 700, "extrabold": 800, "ultrabold": 800,
	"black": 900, "heavy": 900,
}


#: The face a new presentation's words start in when the workspace reads Arabic.
ARABIC = "IBM Plex Sans Arabic"


def arabic(rows: list[dict]) -> None:
	"""Slide rows' words set right to left in the Arabic face, in place: a new
	presentation in a workspace that reads Arabic. Pure."""
	for row in rows:
		drawn = json.loads(row.get("elements") or "[]")
		for one in drawn:
			if one.get("type") != "text" or not isinstance(one.get("content"), str):
				continue
			one["dir"] = "rtl"
			opened = re.sub(r"<(p|h[1-6])(\s[^>]*)?>", lambda m: f"{m[0]}<span style=\"font-family: '{ARABIC}'\">", one["content"])
			one["content"] = re.sub(r"</(p|h[1-6])>", lambda m: f"</span>{m[0]}", opened)
		row["elements"] = json.dumps(drawn)


def found() -> str | None:
	"""The Fonts folder, if a font was ever added."""
	from onedesk.one_cloud import namespace as ns

	return frappe.db.get_value("File", {"is_folder": 1, "folder": ns.HOME, "file_name": FOLDER_NAME})


def folder() -> str:
	"""The Fonts folder in the company's files, made the first time a font is added."""
	from onedesk.one_cloud import namespace as ns

	if found():
		return found()
	made = frappe.get_doc({"doctype": "File", "is_folder": 1, "folder": ns.HOME, "file_name": FOLDER_NAME})
	made.flags.ignore_permissions = True
	try:
		made.insert()
	except frappe.DuplicateEntryError:
		return found()
	return made.name


def _ext(file_name: str) -> str:
	return (file_name or "").rsplit(".", 1)[-1].lower() if "." in (file_name or "") else ""


def clean(family: str) -> str:
	"""A family's name as a stylesheet may quote it. Pure."""
	return " ".join(re.sub(r"[^\w \-]", "", family or "", flags=re.U).split())[:60]


def named(file_name: str, content: bytes | None = None) -> tuple[str, int, str]:
	"""A face's family, weight and style: from the font's own name table where
	it can be read, else from its file's name ("Cairo Bold.ttf"). Pure."""
	stem = (file_name or "").rsplit(".", 1)[0]
	family, weight, style = None, 400, "normal"
	words = []
	for token in re.split(r"[\s_\-]+", stem):
		lower = token.lower()
		if lower.isdigit() and len(lower) == 3 and lower[0] in "123456789" and lower.endswith("00"):
			weight = int(lower)
			continue
		hit = False
		for word, value in WEIGHTS.items():
			if lower.startswith(word):
				weight, hit = value, True
				lower = lower[len(word):]
				break
		if "italic" in lower or "oblique" in lower:
			style, hit = "italic", True
		if not hit:
			words.append(token)
	if content and _ext(file_name) in ("ttf", "otf"):
		family = _family_in(content)
	return clean(family or " ".join(words)) or _("Untitled Font"), weight, style


def _family_in(content: bytes) -> str | None:
	"""The family a TrueType or OpenType file names itself. Pure."""
	try:
		tables = struct.unpack(">H", content[4:6])[0]
		for at in range(tables):
			tag, _sum, offset, _length = struct.unpack(">4sIII", content[12 + at * 16 : 28 + at * 16])
			if tag != b"name":
				continue
			_format, count, strings = struct.unpack(">HHH", content[offset : offset + 6])
			found = {}
			for one in range(count):
				platform, _enc, _lang, name_id, length, start = struct.unpack(">HHHHHH", content[offset + 6 + one * 12 : offset + 18 + one * 12])
				if name_id not in (1, 16) or name_id in found:
					continue
				raw = content[offset + strings + start : offset + strings + start + length]
				found[name_id] = raw.decode("utf-16-be" if platform in (0, 3) else "mac_roman", "ignore")
			return found.get(16) or found.get(1)
	except (struct.error, IndexError):
		return None
	return None


def faces() -> list[dict]:
	"""The workspace's own faces, each its File, family, weight and style."""
	out = []
	held = found()
	if not held:
		return out
	for row in frappe.get_all(
		"File", filters={"folder": held, "is_folder": 0}, fields=["name", "file_name", "content_hash"], order_by="file_name asc"
	):
		if _ext(row.file_name) not in KINDS:
			continue
		family, weight, style = named(row.file_name)
		out.append({"file": row.name, "family": family, "weight": weight, "style": style, "kind": _ext(row.file_name), "hash": (row.content_hash or row.name)[:10]})
	return out


def _may_add() -> bool:
	from onedesk.one import rights

	return rights.held("Presentation", "slide_template")


@frappe.whitelist()
@frappe.read_only()
def library() -> dict:
	"""What every font picker offers: the shipped faces by group and the
	workspace's own by family, and whether this person may add one."""
	from onedesk.trust_center import services

	yours = {}
	for one in faces():
		yours.setdefault(one["family"], []).append({"weight": one["weight"], "style": one["style"]})
	return {
		"shipped": list(SHIPPED),
		"yours": [{"family": family, "faces": held} for family, held in sorted(yours.items())],
		"may_add": _may_add(),
		"google": services.on(SERVICE),
	}


def stylesheet() -> str:
	"""An @font-face for each of the workspace's own faces, at our own address. Pure but for the rows."""
	out = []
	for one in faces():
		url = f"/api/method/onedesk.one_deck.fonts.face?id={one['file']}&v={one['hash']}"
		out.append(
			"@font-face {"
			f"font-family: '{one['family']}'; src: url('{url}') format('{FORMATS[one['kind']]}'); "
			f"font-weight: {one['weight']}; font-style: {one['style']}; font-display: swap;"
			"}"
		)
	return "\n".join(out) + "\n"


@frappe.whitelist(allow_guest=True, methods=["GET"])
def css():
	"""The workspace's own faces as a stylesheet, which the editors, the PDF and
	the screens load beside the shipped one. Fonts are no secret, and a screen
	signs in as nobody."""
	from werkzeug.wrappers import Response

	return Response(stylesheet(), mimetype="text/css", headers={"Cache-Control": "public, max-age=300"})


@frappe.whitelist(allow_guest=True, methods=["GET"])
def face(id: str, v: str | None = None):
	"""One face's bytes from where the File keeps them, at our own address, so a
	browser loads it without asking R2 for permission across sites. The
	address carries the content's hash, so it is cached for good."""
	from werkzeug.wrappers import Response

	row = frappe.db.get_value("File", id, ["file_name", "file_url", "folder", "is_folder"], as_dict=True)
	if not row or row.is_folder or row.folder != found() or _ext(row.file_name) not in KINDS:
		raise frappe.DoesNotExistError
	return Response(
		_bytes(id, row.file_url),
		mimetype=KINDS[_ext(row.file_name)],
		headers={"Cache-Control": "public, max-age=31536000, immutable"},
	)


def _bytes(name: str, url: str) -> bytes:
	from onedesk.one_cloud import store

	if store.is_stored(url):
		return store.get(store.key_of(url))
	return frappe.get_doc("File", name).get_content()


def _kept(family: str, weight: int, style: str, kind: str, content: bytes) -> str:
	"""A face kept in the Fonts folder under the name it is read back by,
	replacing one of the same family, weight and style."""
	file_name = f"{family} {weight}{' Italic' if style == 'italic' else ''}.{kind}"
	for old in frappe.get_all("File", filters={"folder": folder(), "file_name": file_name}, pluck="name"):
		frappe.delete_doc("File", old, ignore_permissions=True)
	made = frappe.get_doc({"doctype": "File", "folder": folder(), "file_name": file_name, "content": content, "is_private": 0})
	made.flags.ignore_permissions = True
	made.insert()
	return made.name


def _adding() -> None:
	if not _may_add():
		frappe.throw(_("Your role doesn't add fonts to the workspace. Ask a workspace administrator."), frappe.PermissionError)


@frappe.whitelist(methods=["POST"])
def upload() -> dict:
	"""A font file of the company's own, added to the workspace."""
	_adding()
	sent = frappe.request.files.get("file")
	if not sent or _ext(sent.filename) not in KINDS:
		frappe.throw(_("Could not add the font: choose a .ttf, .otf, .woff or .woff2 file."))
	content = sent.stream.read(MOST + 1)
	if len(content) > MOST:
		frappe.throw(_("Could not add the font: it is larger than 8 MB."))
	family, weight, style = named(sent.filename, content)
	_kept(family, weight, style, _ext(sent.filename), content)
	return library()


def _get(url: str, **params):
	import requests

	answer = requests.get(url, params=params, timeout=30, headers={"User-Agent": "One"})
	answer.raise_for_status()
	return answer


def _catalogue() -> list[dict]:
	"""Google's catalogue, asked once a day, by our server."""
	from onedesk.trust_center import services

	held = frappe.cache.get_value("one_google_fonts")
	if held is not None:
		return held
	said = services.call(SERVICE, _get, CATALOGUE)
	if said is None:
		return []
	text = said.text
	held = [
		{"family": one["family"], "category": one.get("category", ""), "arabic": "arabic" in (one.get("subsets") or []), "weights": sorted(one.get("fonts") or {})}
		for one in json.loads(text[text.index("{") :]).get("familyMetadataList", [])
	]
	frappe.cache.set_value("one_google_fonts", held, expires_in_sec=86400)
	return held


@frappe.whitelist()
def google_search(q: Annotated[str, "Words in the family's name."] = "") -> list[dict]:
	"""Families in Google's catalogue whose name has these words, the most used first."""
	_adding()
	words = (q or "").lower().split()
	found = [one for one in _catalogue() if all(word in one["family"].lower() for word in words)]
	return [{"family": one["family"], "category": one["category"], "arabic": one["arabic"]} for one in found[:40]]


@frappe.whitelist(methods=["POST"])
def google_add(family: Annotated[str, "A family's name as Google's catalogue has it."]) -> dict:
	"""A family from Google's catalogue, regular and bold, downloaded once and
	kept in the workspace; nobody's browser asks Google for it again."""
	from onedesk.trust_center import services

	_adding()
	known = next((one for one in _catalogue() if one["family"] == family), None)
	if not known:
		frappe.throw(_("Could not add the font: {0} is not in Google's catalogue.").format(family))
	weights = [weight for weight in ("400", "700") if weight in known["weights"]] or known["weights"][:1]
	sheet = services.call(SERVICE, _get, SHEET, family=f"{family}:wght@{';'.join(weights)}" if weights != ["400"] else family)
	if sheet is None:
		frappe.throw(_("Could not add the font: Google Fonts is off for this workspace."))
	for body in re.findall(r"@font-face \{(.*?)\}", sheet.text, re.S):
		url = re.search(r"url\((https://fonts\.gstatic\.com/[^)]+)\)", body)
		weight = re.search(r"font-weight: (\d+)", body)
		if not url or not weight:
			continue
		kind = _ext(url[1].split("?")[0])
		if kind not in KINDS:
			continue
		content = services.call(SERVICE, _get, url[1]).content
		_kept(clean(family), int(weight[1]), "normal", kind, content)
	return library()
