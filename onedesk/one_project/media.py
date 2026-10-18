"""A project's Featured Media: the photos and videos it is shown with."""

import mimetypes

import frappe
from frappe import _

PREFIX = "@featured/"

FOLDER = "Featured Media"

KINDS = ("image/", "video/")


def node(project: str) -> str:
	return f"{PREFIX}{project}"


def project_of(node_id: str) -> str | None:
	"""The project a Featured Media node is of, or None. Pure."""
	return node_id[len(PREFIX) :] or None if (node_id or "").startswith(PREFIX) else None


def kind_of(file_name: str | None) -> str | None:
	"""photo, video, or None for anything else. Pure."""
	found = mimetypes.guess_type(file_name or "")[0] or ""
	if found.startswith("image/"):
		return "photo"
	if found.startswith("video/"):
		return "video"
	return None


def check(file_name: str) -> None:
	if not kind_of(file_name):
		frappe.throw(_("Only photos and videos go in Featured Media. {0} is neither.").format(file_name))


def rows(project: str, fields: list | None = None) -> list[dict]:
	"""The project's featured files, newest first."""
	return frappe.get_all(
		"File",
		filters={
			"attached_to_doctype": "Project",
			"attached_to_name": project,
			"one_featured": 1,
			"is_folder": 0,
		},
		fields=fields or ["name", "file_name", "file_url", "thumbnail_url", "creation"],
		order_by="creation desc",
	)


def cover_of(project: str, without: str | None = None) -> str | None:
	"""The newest photo's address, or None. Videos are shown, not made covers."""
	for one in rows(project, ["name", "file_name", "file_url"]):
		if one.name != without and kind_of(one.file_name) == "photo":
			return one.file_url
	return None


def settle_cover(project: str, without: str | None = None) -> None:
	"""Project.one_cover follows the folder, and an open page redraws."""
	if not frappe.db.exists("Project", project):
		return
	cover = cover_of(project, without)
	if frappe.db.get_value("Project", project, "one_cover") != cover:
		frappe.db.set_value("Project", project, "one_cover", cover, update_modified=False)
	frappe.publish_realtime(
		"one_project_media", {"project": project}, doctype="Project", docname=project, after_commit=True
	)


def changed(doc, method=None) -> None:
	"""File after_insert, on_update and on_trash: a featured file of a
	project, or one that just stopped being one, settles the cover."""
	if doc.attached_to_doctype != "Project" or not doc.attached_to_name:
		return
	before = doc.get_doc_before_save() if method == "on_update" else None
	if doc.get("one_featured") or (before and before.get("one_featured")):
		settle_cover(doc.attached_to_name, without=doc.name if method == "on_trash" else None)


def handing_over(doc) -> None:
	"""CloudFile.on_trash: a featured photo that is its project's Cover is
	replaced by the next one before it goes."""
	if doc.attached_to_doctype != "Project" or not doc.attached_to_name or not doc.get("one_featured"):
		return
	if frappe.db.get_value("Project", doc.attached_to_name, "one_cover") == doc.file_url:
		settle_cover(doc.attached_to_name, without=doc.name)


def kept_shown(doc, method=None) -> None:
	"""File validate: a featured file is a photo or a video and opens for
	anybody, however it is featured (the page, a bulk edit, an import)."""
	if not doc.get("one_featured"):
		return
	check(doc.file_name)
	doc.is_private = 0


def feature(name: str, on: bool) -> None:
	"""Put one of a project's files in its Featured Media, or take it out."""
	doc = frappe.get_doc("File", name)
	if on:
		check(doc.file_name)
	doc.one_featured = 1 if on else 0
	doc.is_private = 0 if on else 1
	doc.flags.ignore_permissions = True
	doc.save()


@frappe.whitelist()
@frappe.read_only()
def featured(project: str) -> list[dict]:
	"""What the project is shown with, newest first: for its page and portal."""
	frappe.has_permission("Project", "read", doc=project, throw=True)
	return shown(project)


def shown(project: str) -> list[dict]:
	"""The project's photos and videos in the order they're shown: its Cover
	first, then the rest newest first."""
	cover = frappe.db.get_value("Project", project, "one_cover")
	found = [
		{
			"name": one.name,
			"title": one.file_name,
			"url": one.file_url,
			"thumbnail": one.thumbnail_url,
			"kind": kind_of(one.file_name),
		}
		for one in rows(project)
		if kind_of(one.file_name)
	]
	return sorted(found, key=lambda one: one["url"] != cover)


@frappe.whitelist(methods=["POST"])
def add() -> dict:
	"""frappe's upload dialog on the project's page, sent here (its `method`):
	the file goes in the project's Featured Media. frappe's upload_file has
	read the file and checked the project may be written to."""
	from onedesk.one_storage import api, upload

	content = getattr(frappe.local, "uploaded_file", None)
	if content is None:
		frappe.throw(_("Choose a photo or a video from your computer."))
	project = frappe.form_dict.docname
	if frappe.form_dict.doctype != "Project" or not project:
		frappe.throw(_("Photos and videos are added to a project."))
	name = api._clean(frappe.local.uploaded_filename) or "file"
	upload._place(node(project), None, {"file_name": name, "content": content})
	return {"project": project}
