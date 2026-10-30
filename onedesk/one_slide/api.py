# Parts derived from frappe/suite@2831a5d (suite/slides/api/slides.py, suite/slides/api/file.py and
# suite/slides/doctype/presentation/presentation.py). Copyright (c) Frappe Technologies Pvt. Ltd. AGPL-3.0.
"""What the presentation editor calls: make one in a folder, open it, save its
slides, rename it, and keep the pictures and videos put on it. Whether the
reader may is OneCloud's answer for the File the presentation sits behind,
never the Presentation's own permissions. AGENTS.md, api.py.

Suite's editor calls these by Suite's names (`shim/frappe-ui.js` points them
here), so the names and what they answer are Suite's.
"""

import base64
import json
import mimetypes
import random
import re
import string
import uuid
from urllib.parse import parse_qs, urlparse

import frappe
from frappe import _
from frappe.utils import cstr

PRESENTATION = "Presentation"
SLIDE = "Presentation Slide"

#: Where a presentation's File points, so OneCloud knows to open it in the editor.
URL = "/api/method/onedesk.one_slide.api.download?presentation="

#: Where a picture or video on a slide is read from: through the presentation,
#: so only those who may open it see what is in it.
MEDIA = "/api/method/onedesk.one_slide.api.media?id="

#: The theme a blank presentation starts from (templates/system.json).
LIGHT = "1mjgj61m8j"

MOST_TITLE = 140

#: The most one save may carry, every slide's elements together.
MOST_BYTES = 25 * 1024 * 1024

#: The largest picture or video one upload may put on a slide.
MOST_MEDIA = 200 * 1024 * 1024

MOST_THUMBNAIL = 6 * 1024 * 1024

#: The longest a slide's speaker notes may be.
MOST_NOTES = 20000

#: The only fields the editor may set on a slide (Suite's SLIDE_FIELDS).
SLIDE_FIELDS = frozenset(
	{"client_id", "background", "elements", "transition", "transition_duration", "fade_unmatched_elements", "advance_after", "notes", "hide_master", "layout"}
)

PICTURES = {"png", "jpg", "jpeg", "gif", "webp"}


def presentation_of(url: str | None) -> str | None:
	"""The presentation a File's URL names, or None. Pure."""
	if not url or not url.startswith(URL):
		return None
	return (parse_qs(urlparse(url).query).get("presentation") or [None])[0]


def _file(name: str) -> dict:
	from onedesk.one_storage import namespace as ns

	held = frappe.db.get_value(PRESENTATION, name, ["file", "is_template", "master_of"], as_dict=True)
	if held and held.master_of:
		# a master is opened, and kept, with the presentation it is the master of
		held = frappe.db.get_value(PRESENTATION, held.master_of, ["file", "is_template"], as_dict=True)
	item = ns.row(held.file) if held and held.file else None
	if not item or item.get("one_deleted_on"):
		frappe.throw(_("This presentation no longer exists."), frappe.DoesNotExistError)
	return item


def _may(name: str, ptype: str = "read") -> dict:
	from onedesk.one_storage import namespace as ns

	item = _file(name)
	if not ns.may(item, ptype):
		frappe.throw(_("You do not have permission to open this presentation."), frappe.PermissionError)
	return item


def frame(name: str) -> tuple[int, int]:
	"""The presentation's size in pixels: every slide of it is this size."""
	width, height = frappe.db.get_value(PRESENTATION, name, ["width", "height"]) or (0, 0)
	return (int(width or 960), int(height or 540))


def _titled(title: str | None) -> str:
	return " ".join((title or "").replace("/", " ").split())[:MOST_TITLE]


@frappe.whitelist(methods=["POST"])
def make(parent: str, title: str | None = None, template: str | None = None, width: int | None = None, height: int | None = None) -> dict:
	"""A new presentation in a OneCloud folder or on a record, from a theme's
	title slide or a copy of a saved template, at the size asked (the
	template's own when none is), and the node the explorer draws."""
	from onedesk.one_slide import resize
	from onedesk.one_storage import api as cloud
	from onedesk.one_storage import namespace as ns

	where = cloud._target(parent)
	if where[0] == "mount":
		frappe.throw(_("Presentations cannot be created in a mounted drive."))
	title = _titled(title) or _("Untitled Presentation")
	source = template if template and frappe.db.get_value(PRESENTATION, template, "is_template") else LIGHT
	drawn = frame(source)
	size = resize.size(width, height) if width and height else drawn
	doc = frappe.get_doc({"doctype": PRESENTATION, "title": title, "theme": source, "width": size[0], "height": size[1]})
	doc.flags.ignore_permissions = True
	doc.insert()
	first = _first_slides(source)
	resize.refit(first, drawn, size)
	doc.set("slides", first)
	doc.save(ignore_permissions=True)
	if source != LIGHT:
		from onedesk.one_slide import master

		# a template's master comes with it, at the size asked
		master.copy(source, doc.name)
		if drawn != size and master.of(doc.name):
			resize.redrawn(master.of(doc.name), drawn, size)
	file = {"doctype": "File", "file_url": URL + doc.name, "is_private": 1}
	if where[0] == "folder":
		file.update(folder=where[1], file_name=ns.unique_name(title, cloud._taken(where[1])))
	else:
		file.update(attached_to_doctype=where[1], attached_to_name=where[2], file_name=title)
	made = frappe.get_doc(file)
	made.flags.ignore_permissions = True
	made.insert()
	doc.db_set("file", made.name)
	return {**ns.node(ns.row(made.name)), "presentation": doc.name}


def make_with(parent: str, title: str, slides: list[dict]) -> str:
	"""A presentation of slides drawn elsewhere (`convert.slide`, a picture or
	a video), made where `make` makes one: its File's name. Not whitelisted:
	OneDisplay's patch and demo call it."""
	from onedesk.one_slide import play

	made = make(parent, title)
	doc = frappe.get_doc(PRESENTATION, made["presentation"])
	doc.set(
		"slides",
		[
			{"client_id": str(uuid.uuid4()), "background": play.background(one.get("background")), "elements": play.cleaned(one.get("elements"))}
			for one in slides
		],
	)
	doc.save(ignore_permissions=True)
	return doc.file


def _first_slides(template: str) -> list[dict]:
	"""A theme starts from its title slide; a saved template is copied whole."""
	source = frappe.get_doc(PRESENTATION, template)
	rows = source.slides[2:3] if source.name in _system() and len(source.slides) > 2 else source.slides
	out = []
	from onedesk.one_slide import layouts

	for row in rows or source.slides[:1]:
		elements = json.loads(row.elements or "[]")
		for one in elements:
			# where each came from, so the layout's look can be brought in again (layouts.py)
			one["from"] = one.get("id")
		_new_ids(elements)
		out.append(
			{
				"layout": layouts.ref(source.name, row.client_id) if row.client_id else None,
				"client_id": str(uuid.uuid4()),
				"background": row.background,
				"elements": json.dumps(elements),
				"transition": row.transition,
				"transition_duration": row.transition_duration,
				"fade_unmatched_elements": row.fade_unmatched_elements,
				"advance_after": row.advance_after,
				"notes": row.notes,
			}
		)
	return out


def _system() -> set:
	from onedesk.one_slide import setup

	return {one["name"] for one in setup.system()}


@frappe.whitelist()
@frappe.read_only()
def listed() -> list[dict]:
	"""The presentations kept as templates that the reader may use, by title."""
	from onedesk.one_storage import namespace as ns

	out = []
	for one in frappe.get_all(PRESENTATION, filters={"is_template": 1, "file": ["is", "set"]}, fields=["name", "file"], order_by="title asc"):
		item = ns.row(one.file)
		if item and not item.get("one_deleted_on") and ns.may(item, "read"):
			out.append({"name": one.name, "title": item["file_name"]})
	return out


@frappe.whitelist()
@frappe.read_only()
def search(doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters=None, **kwargs) -> list:
	"""Presentations the person picking may open, for a field that links a
	presentation's File (a slide playlist's row): its name and its title."""
	from onedesk.one_storage import namespace as ns

	found = []
	for one in frappe.get_all(
		"File",
		filters={"file_url": ["like", f"{URL}%"], "file_name": ["like", f"%{txt or ''}%"]},
		fields=["name", "file_name"],
		order_by="modified desc",
		limit=200,
	):
		item = ns.row(one.name)
		if item and not item.get("one_deleted_on") and ns.may(item, "read"):
			found.append([one.name, one.file_name])
	start = int(start or 0)
	return found[start : start + int(page_len or 20)]


@frappe.whitelist()
@frappe.read_only()
def get(name: str, doctype: str | None = None) -> dict:
	"""The presentation as the editor loads it (Suite reads it with
	frappe.client.get), with what OneCloud says about it."""
	item = _may(name, "read")
	return _loaded(name, item)


def _loaded(name: str, item: dict) -> dict:
	from onedesk.one import rights
	from onedesk.one_storage import namespace as ns

	doc = frappe.get_doc(PRESENTATION, name).as_dict(no_default_fields=False)
	doc["title"] = item["file_name"]
	doc["file"] = item["name"]
	doc["can_write"] = ns.may(item, "write")
	doc["can_template"] = rights.held(PRESENTATION, "slide_template")
	doc["record"] = (
		{"doctype": item["attached_to_doctype"], "name": item["attached_to_name"]}
		if item.get("attached_to_doctype") and item.get("attached_to_name")
		else None
	)
	doc["trail"] = ns.trail(item["folder"]) if item.get("folder") and not item.get("attached_to_doctype") else []
	for row in doc.get("slides") or []:
		row.pop("played", None)
	from onedesk.one_slide import master

	# what every slide draws underneath; a master's own title is the presentation's
	doc["master"] = [] if doc.get("master_of") else master.elements(name)
	if doc.get("master_of"):
		doc["title"] = _("Master of {0}").format(item["file_name"])
	for hook in frappe.get_hooks("one_slide_loaded"):
		frappe.get_attr(hook)(doc, item)
	return doc


@frappe.whitelist()
@frappe.read_only()
def get_editor_access(presentation_id: str, doctype: str | None = None) -> str:
	from onedesk.one_storage import namespace as ns

	try:
		item = _may(presentation_id, "read")
	except (frappe.PermissionError, frappe.DoesNotExistError):
		return "none"
	return "edit" if ns.may(item, "write") else "view"


@frappe.whitelist(methods=["POST"])
def save_slides(name: str, slides: list[dict] | str, base_modified: str) -> dict:
	"""Replace a presentation's slides with the editor's list, matched by
	`client_id`. A save built on an older version than the server's would wipe
	rows saved elsewhere, so it is refused rather than merged (Suite's rule)."""
	item = _may(name, "write")
	slides = frappe.parse_json(slides) if isinstance(slides, str) else slides
	size = sum(len(cstr(one.get("elements"))) for one in slides or [])
	if size > MOST_BYTES:
		frappe.throw(_("This presentation is too large to save."))
	doc = frappe.get_doc(PRESENTATION, name)
	if cstr(doc.modified) != cstr(base_modified):
		frappe.throw(
			_("This presentation was changed elsewhere. Reload to get the latest version."), frappe.TimestampMismatchError
		)
	for hook in frappe.get_hooks("one_slide_saving"):
		slides = frappe.get_attr(hook)(name, item, slides or [])
	from onedesk.one_slide import versions

	versions.before_saving(name)
	doc.set("slides", _merged(doc.slides, slides or []))
	doc.byte_size = size
	doc.save(ignore_permissions=True)
	if not doc.master_of:
		frappe.db.set_value("File", item["name"], "file_size", size, update_modified=True)
	return {"modified": doc.modified}


def _merged(existing, incoming):
	from onedesk.one_slide import play

	by_client_id = {row.client_id: row for row in existing if row.client_id}
	rows = []
	for idx, slide in enumerate(incoming, start=1):
		unknown = set(slide) - SLIDE_FIELDS
		if unknown:
			frappe.throw(_("Slide fields not accepted: {0}").format(", ".join(sorted(unknown))))
		slide = {**slide, "elements": play.cleaned(slide.get("elements"))}
		if "background" in slide:
			slide["background"] = play.background(slide["background"])
		if "notes" in slide:
			# plain words, drawn as text wherever they are shown, so kept as typed
			slide["notes"] = str(slide["notes"] or "")[:MOST_NOTES]
		row = by_client_id.pop(slide.get("client_id"), None)
		if row:
			row.update(slide)
		else:
			row = frappe.new_doc(SLIDE).update(slide)
		row.idx = idx
		rows.append(row)
	return rows


@frappe.whitelist(methods=["POST"])
def update_title(name: str, title: str) -> dict:
	item = _may(name, "write")
	base_modified = frappe.db.get_value(PRESENTATION, name, "modified")
	_retitle(name, item, title)
	modified = frappe.db.get_value(PRESENTATION, name, "modified")
	return {"slug": _titled(title).lower().replace(" ", "-"), "modified": modified, "base_modified": base_modified}


@frappe.whitelist(methods=["POST"])
def rename_presentation(name: str, title: str) -> dict:
	item = _may(name, "write")
	_retitle(name, item, title)
	return {"name": name, "title": frappe.db.get_value("File", item["name"], "file_name")}


def _retitle(name: str, item: dict, title: str | None) -> None:
	"""The File's name is the presentation's title, kept unique in its folder."""
	from onedesk.one_storage import api as cloud
	from onedesk.one_storage import namespace as ns

	title = _titled(title)
	if not title or title == item["file_name"]:
		return
	if item.get("folder") and not item.get("attached_to_doctype"):
		title = ns.unique_name(title, cloud._taken(item["folder"], but=item["name"]))
	frappe.db.set_value("File", item["name"], "file_name", title)
	doc = frappe.get_doc(PRESENTATION, name)
	doc.title = title
	doc.save(ignore_permissions=True)


@frappe.whitelist(methods=["POST"])
def update_theme(name: str, theme: str) -> dict:
	_may(name, "write")
	if not frappe.db.get_value(PRESENTATION, theme, "is_template"):
		frappe.throw(_("That theme does not exist."), frappe.DoesNotExistError)
	doc = frappe.get_doc(PRESENTATION, name)
	base_modified = doc.modified
	doc.theme = theme
	doc.save(ignore_permissions=True)
	return {"modified": doc.modified, "base_modified": base_modified}


@frappe.whitelist()
@frappe.read_only()
def get_templates() -> list[dict]:
	"""The themes, each with its layouts, which a slide is inserted from."""
	templates = frappe.get_all(
		PRESENTATION,
		filters={"is_template": 1},
		fields=["name", "title", "slug", "creation", "is_template"],
		order_by="creation",
	)
	rows = frappe.get_all(
		SLIDE,
		filters={"parent": ["in", [one.name for one in templates] or [""]], "parenttype": PRESENTATION},
		fields=["name", "parent", "idx", "client_id", "background", "elements", "transition", "transition_duration", "fade_unmatched_elements", "advance_after"],
		order_by="parent asc, idx asc",
	)
	from onedesk.one_storage import namespace as ns

	system = _system()
	files = dict(frappe.get_all(PRESENTATION, filters={"is_template": 1}, fields=["name", "file"], as_list=True))
	sizes = {
		one.name: (one.width or 960, one.height or 540)
		for one in frappe.get_all(PRESENTATION, filters={"is_template": 1}, fields=["name", "width", "height"])
	}
	templates = [one for one in templates if one.name in system or (files.get(one.name) and _readable(ns, files[one.name]))]
	by_template = {}
	for row in rows:
		row["doctype"] = SLIDE
		by_template.setdefault(row["parent"], []).append(row)
	for one in templates:
		one["layouts"] = by_template.get(one.name, [])
		for layout in one["layouts"]:
			# the size it was drawn at, so the editor fits it to the presentation's (shim/resize.js)
			layout["width"], layout["height"] = sizes.get(one.name) or (960, 540)
			layout["thumbnail"] = (
				f"/assets/onedesk/slide/frontend/images/layouts/{one.title.lower()}/thumbnail-{layout['idx']}.webp"
				if one.name in system
				else ""
			)
	return templates


def _readable(ns, file: str) -> bool:
	item = ns.row(file)
	return bool(item and not item.get("one_deleted_on") and ns.may(item, "read"))


def _new_ids(elements: list) -> None:
	"""Fresh ids for a copied set: connector ends inside the set follow the
	copies, the rest are dropped (Suite's remap_element_ids)."""
	new_ids = ["".join(random.choices(string.ascii_lowercase + string.digits, k=9)) for _ in elements]
	moved = {one.get("id"): new for one, new in zip(elements, new_ids, strict=True)}
	for one, new in zip(elements, new_ids, strict=True):
		one["id"] = new
		connector = one.get("connector")
		if not connector:
			continue
		for end in ("start", "end"):
			bound = connector.get(end)
			if bound:
				target = moved.get(bound.get("elementId"))
				connector[end] = {**bound, "elementId": target} if target else None


@frappe.whitelist(methods=["POST"])
def update_slide_attachments(parent: str, slide: dict | str) -> dict:
	"""A layout or a pasted slide: fresh ids, and its pictures kept on this
	presentation."""
	_may(parent, "write")
	slide = frappe.parse_json(slide) if isinstance(slide, str) else slide
	held = slide.get("elements") or "[]"
	elements = held if isinstance(held, list) else json.loads(held)
	_new_ids(elements)
	for one in elements:
		_adopted(parent, one)
	slide["elements"] = json.dumps(elements)
	return slide


@frappe.whitelist(methods=["POST"])
def get_updated_json(presentation: str, elements: list[dict] | str) -> list:
	"""Elements pasted from another presentation keep their pictures, copied
	onto this one so whoever may open this one sees them."""
	_may(presentation, "write")
	elements = frappe.parse_json(elements) if isinstance(elements, str) else elements
	for one in elements or []:
		_adopted(presentation, one)
	return elements


def _adopted(presentation: str, element: dict) -> None:
	for key in ("src", "poster"):
		url = element.get(key)
		if not isinstance(url, str) or not url.startswith(MEDIA):
			continue
		held = _media_row(url[len(MEDIA) :])
		if not held or held.attached_to_name == presentation:
			continue
		try:
			_may(held.attached_to_name, "read")
		except (frappe.PermissionError, frappe.DoesNotExistError):
			element[key] = ""
			continue
		made = _kept(presentation, held.file_name, frappe.get_doc("File", held.name).get_content())
		element[key] = made["file_url"]
		if key == "src":
			element["attachmentName"] = made["name"]


def _media_row(name: str):
	return frappe.db.get_value("File", name, ["name", "attached_to_doctype", "attached_to_name", "file_name", "file_url"], as_dict=True)


@frappe.whitelist(methods=["POST"])
def upload() -> dict:
	"""A picture or video put on a slide (frappe-ui's FileUploadHandler sends
	it here): a private File kept on the presentation, read back through `media`."""
	name = frappe.form_dict.docname
	_may(name, "write")
	sent = frappe.request.files.get("file")
	if not sent:
		frappe.throw(_("No file was sent."))
	content = sent.stream.read()
	if len(content) > MOST_MEDIA:
		frappe.throw(_("This file is too large to put on a slide."))
	return _kept(name, sent.filename, content)


def _kept(name: str, file_name: str, content: bytes) -> dict:
	made = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": file_name,
			"content": content,
			"is_private": 1,
			"attached_to_doctype": PRESENTATION,
			"attached_to_name": name,
		}
	)
	made.flags.ignore_permissions = True
	made.insert()
	return {"name": made.name, "file_name": made.file_name, "file_url": MEDIA + made.name, "file_size": made.file_size}


@frappe.whitelist(methods=["POST"])
def get_webp_doc(presentation_name: str, file_doc: dict | str) -> dict:
	"""Suite turns a picture into WebP here. Ours is kept as it was sent."""
	_may(presentation_name, "write")
	return frappe.parse_json(file_doc) if isinstance(file_doc, str) else file_doc


@frappe.whitelist(methods=["POST"])
def save_base64_image(base64_data: str, presentation_name: str, prefix: str) -> str:
	"""A video's poster frame, taken in the browser."""
	_may(presentation_name, "write")
	match = re.match(r"^data:image/([a-zA-Z0-9.+-]+);base64,(.+)$", base64_data or "", re.DOTALL)
	if not match or match.group(1).lower() not in PICTURES:
		frappe.throw(_("This is not a picture."))
	try:
		content = base64.b64decode(match.group(2), validate=True)
	except ValueError:
		frappe.throw(_("This is not a picture."))
	if len(content) > MOST_THUMBNAIL:
		frappe.throw(_("This picture is too large."))
	prefix = re.sub(r"[^\w-]", "", prefix or "poster")[:40] or "poster"
	return _kept(presentation_name, f"{prefix}-{uuid.uuid4().hex[:6]}.{match.group(1).lower()}", content)["file_url"]


@frappe.whitelist(methods=["POST"])
def save_presentation_thumbnail(presentation_name: str, base64_data: str) -> str:
	"""The first slide as a picture, for OneCloud to show."""
	_may(presentation_name, "write")
	match = re.match(r"^data:image/webp;base64,(.+)$", base64_data or "", re.DOTALL)
	if not match:
		frappe.throw(_("This is not a picture."))
	content = base64.b64decode(match.group(1), validate=True)
	if len(content) > MOST_THUMBNAIL:
		frappe.throw(_("This picture is too large."))
	old = frappe.db.get_value(PRESENTATION, presentation_name, "thumbnail") or ""
	made = _kept(presentation_name, f"thumbnail-{presentation_name}.webp", content)
	frappe.db.set_value(PRESENTATION, presentation_name, "thumbnail", made["file_url"], update_modified=False)
	if old.startswith(MEDIA) and frappe.db.exists("File", old[len(MEDIA) :]):
		frappe.delete_doc("File", old[len(MEDIA) :], ignore_permissions=True)
	return made["file_url"]


@frappe.whitelist()
def media(id: str) -> None:
	"""A picture or video on a slide, to whoever may open its presentation,
	with ranges so a video can be played from anywhere in it."""
	from werkzeug.utils import send_file

	held = _media_row(id)
	if not held or held.attached_to_doctype != PRESENTATION:
		raise frappe.DoesNotExistError
	_may(held.attached_to_name, "read")
	path = frappe.get_doc("File", id).get_full_path()
	kind = mimetypes.guess_type(held.file_name or path)[0] or "application/octet-stream"
	response = send_file(path, environ=frappe.local.request.environ, conditional=True, mimetype=kind)
	response.headers["Accept-Ranges"] = "bytes"
	response.headers["Cache-Control"] = "private, max-age=86400"
	frappe.local.response = response
	frappe.local.response_type = "raw"


@frappe.whitelist(allow_guest=True, methods=["GET"])
def shown(id: str, sig: str) -> None:
	"""A picture or video on a slide, to a screen: the address carries a seal
	only the site can make for that one file (play.seal), since a screen signs
	in as nobody."""
	import hmac

	from werkzeug.utils import send_file

	from onedesk.one_slide import play

	held = _media_row(id)
	if not held or held.attached_to_doctype != PRESENTATION or not hmac.compare_digest(play.seal(id), str(sig or "")):
		raise frappe.DoesNotExistError
	path = frappe.get_doc("File", id).get_full_path()
	kind = mimetypes.guess_type(held.file_name or path)[0] or "application/octet-stream"
	response = send_file(path, environ=frappe.local.request.environ, conditional=True, mimetype=kind)
	response.headers["Accept-Ranges"] = "bytes"
	response.headers["Cache-Control"] = "public, max-age=604800, immutable"
	frappe.local.response = response
	frappe.local.response_type = "raw"


@frappe.whitelist()
def visited(doctype: str | None = None, docname: str | None = None) -> None:
	"""Suite counts a visit for Drive's recent list; OneCloud keeps its own."""


@frappe.whitelist()
def download(presentation: str) -> None:
	"""A presentation's File opened outside the editor goes to the editor."""
	_may(presentation, "read")
	frappe.local.response["type"] = "redirect"
	frappe.local.response["location"] = f"/desk/presentation/{presentation}"


def copied(doc, method=None) -> None:
	"""File before_insert: a File naming a presentation another File already
	holds is a copy, so it holds a copy of the presentation."""
	name = presentation_of(doc.file_url)
	if not name or not frappe.db.exists("File", {"file_url": doc.file_url}):
		return
	made = frappe.copy_doc(frappe.get_doc(PRESENTATION, name))
	made.title = doc.file_name or made.title
	made.file = None
	made.flags.ignore_permissions = True
	made.insert()
	for row in made.slides:
		elements = json.loads(row.elements or "[]")
		for one in elements:
			_adopted(made.name, one)
		row.elements = json.dumps(elements)
	made.save(ignore_permissions=True)
	from onedesk.one_slide import master

	master.copy(name, made.name)
	doc.file_url = URL + made.name
	doc.content_hash = None
	doc.flags.one_presentation = made.name


def placed(doc, method=None) -> None:
	"""File after_insert: a copied presentation knows its File."""
	if doc.flags.one_presentation:
		frappe.db.set_value(PRESENTATION, doc.flags.one_presentation, "file", doc.name)


def file_gone(doc, method=None) -> None:
	"""File on_trash: the presentation it held goes with it, and its pictures."""
	name = presentation_of(doc.file_url)
	if not name or not frappe.db.exists(PRESENTATION, name):
		return
	from onedesk.one_slide import versions

	for held in frappe.get_all("File", filters={"attached_to_doctype": PRESENTATION, "attached_to_name": name}, pluck="name"):
		frappe.delete_doc("File", held, ignore_permissions=True)
	from onedesk.one_slide import master

	master.forget(name)
	versions.forget(name)
	frappe.delete_doc(PRESENTATION, name, ignore_permissions=True, force=True)
