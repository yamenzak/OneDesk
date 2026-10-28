"""Drawn pictures: a record with no picture of its own gets one DiceBear,
shipped with One, draws on this server from its name, in the style picked for
its record type in One's settings (Pictures). Nothing else is ever replaced;
see AGENTS.md, Drawn pictures."""

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import frappe
from frappe import _

KEY = "one_avatar_styles"

# The record types a style can be picked for: the people and organisations
# OneMail looks for pictures of (faces.DRESSED), but the company, whose logo
# is set beside this.
KINDS = ("Contact", "Lead", "Customer", "Supplier", "Employee", "User", "Manufacturer", "Brand", "Bank")

PREFIX = "drawn-"

# Kept beside OneMail's logos, not attached to the record, so a drawn picture
# is no attachment of it and says nothing in its activity.
FOLDER, FOLDER_NAME = "Home/Pictures", "Pictures"

PATIENCE = 120

NOBODY = ("Administrator", "Guest")


def _script() -> Path:
	return Path(frappe.get_app_path("onedesk")).parent / "frontend" / "avatars" / "draw.mjs"


def _node(verb: str, asked=None):
	node = shutil.which("node")
	if not node:
		frappe.throw(_("Pictures can't be drawn on this server."))
	script = _script()
	done = subprocess.run(
		[node, str(script), verb],
		input=json.dumps(asked or []),
		capture_output=True,
		text=True,
		cwd=script.parent,
		timeout=PATIENCE,
		check=True,
	)
	return json.loads(done.stdout)


def styles() -> list[dict]:
	"""Every style DiceBear ships: key, title, creator and licence."""
	return frappe.cache.get_value("one_avatar_styles_known", lambda: _node("styles"))


def chosen() -> dict:
	"""{record type: style} the workspace picked."""
	try:
		said = json.loads(frappe.db.get_default(KEY) or "{}")
	except ValueError:
		return {}
	return {kind: style for kind, style in said.items() if kind in KINDS and style}


def style_for(doctype: str) -> str | None:
	return chosen().get(doctype)


def field_of(doctype: str) -> str:
	from onedesk.one_mail.faces import DRESSED

	return DRESSED[doctype][0]


def is_drawn(url: str | None) -> bool:
	return bool(url) and url.rsplit("/", 1)[-1].startswith(PREFIX)


def style_of(url: str | None) -> str | None:
	"""The style a drawn picture was drawn in. Pure."""
	if not is_drawn(url):
		return None
	return url.rsplit("/", 1)[-1][len(PREFIX) :].rsplit("-", 1)[0]


def file_name(style: str, doctype: str, name: str) -> str:
	"""Pure: one name per record and style."""
	digest = hashlib.sha1(f"{doctype}:{name}".encode()).hexdigest()[:12]
	return f"{PREFIX}{style}-{digest}.svg"


def draw(asked: list[tuple[str, str]]) -> list[str | None]:
	"""SVGs for [(style, seed)], in one run of node."""
	return _node("draw", [{"style": style, "seed": seed} for style, seed in asked]) if asked else []


def _seed(doctype: str) -> str:
	"""The name a record type's gallery is drawn from: its newest record's."""
	names = frappe.get_all(doctype, pluck="name", limit=1, order_by="creation desc") if doctype in KINDS else []
	return names[0] if names else "Mariam"


@frappe.whitelist()
def gallery(doctype: str) -> dict:
	"""Every style, drawn from one of the record type's own names, for the
	picker in One's settings › Pictures: {style: svg}."""
	from onedesk.one import roles

	roles.require()
	if doctype not in KINDS:
		frappe.throw(_("Pictures can't be drawn for this record type."))
	keys = [one["key"] for one in styles()]
	seed = _seed(doctype)
	return dict(zip(keys, draw([(key, seed) for key in keys]), strict=True))


def _folder() -> str:
	if not frappe.db.exists("File", FOLDER):
		doc = frappe.get_doc({"doctype": "File", "is_folder": 1, "file_name": FOLDER_NAME, "folder": "Home"})
		doc.flags.ignore_permissions = True
		doc.insert()
	return FOLDER


def _keep(doctype: str, name: str, style: str, svg: str) -> str:
	field = field_of(doctype)
	doc = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": file_name(style, doctype, name),
			"folder": _folder(),
			"is_private": 0,
			"content": svg,
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert()
	frappe.db.set_value(doctype, name, field, doc.file_url, update_modified=False)
	return doc.file_url


def _forget(url: str) -> None:
	for one in frappe.get_all("File", filters={"file_url": url, "folder": FOLDER}, pluck="name"):
		frappe.delete_doc("File", one, ignore_permissions=True, force=True)


def dress(doctype: str, name: str) -> str | None:
	"""A record still without a picture gets one drawn, when its type has a
	style (faces.dress, after Gravatar found nothing)."""
	style = style_for(doctype)
	if not style or (doctype == "User" and name in NOBODY):
		return None
	field = field_of(doctype)
	if frappe.db.get_value(doctype, name, field):
		return None
	svg = draw([(style, name)])[0]
	return _keep(doctype, name, style, svg) if svg else None


def fill(doctype: str) -> int:
	"""After the style of a record type is picked or changed: every record
	without a picture gets one, every drawn one is redrawn in the new style,
	and with no style the drawn ones are taken off. A picture somebody put
	there, or Gravatar's, is left as it is. Safe to run again."""
	field = field_of(doctype)
	style = style_for(doctype)
	rows = frappe.get_all(doctype, fields=["name", field], limit=0)
	wanted = [
		one
		for one in rows
		if not (doctype == "User" and one.name in NOBODY)
		and ((not one.get(field) and style) or (is_drawn(one.get(field)) and style_of(one.get(field)) != style))
	]
	changed = 0
	for start in range(0, len(wanted), 200):
		batch = wanted[start : start + 200]
		svgs = draw([(style, one.name) for one in batch]) if style else [None] * len(batch)
		for one, svg in zip(batch, svgs, strict=True):
			old = one.get(field)
			if old and not is_drawn(old):
				continue
			if old:
				_forget(old)
				frappe.db.set_value(doctype, one.name, field, None, update_modified=False)
			if svg:
				_keep(doctype, one.name, style, svg)
			changed += 1
		frappe.db.commit()
	return changed


@frappe.whitelist(methods=["POST"])
def pick(doctype: str, style: str | None = None) -> dict:
	"""One's settings › Pictures: the style for one record type, or none,
	saved as it is picked; its records are filled again in the background."""
	from onedesk.one import roles

	roles.require()
	style = (style or "").strip()
	if doctype not in KINDS or not frappe.db.exists("DocType", doctype):
		frappe.throw(_("Pictures can't be drawn for this record type."))
	if style and style not in {one["key"] for one in styles()}:
		frappe.throw(_("There is no such picture style."))
	now = chosen()
	if now.get(doctype, "") == style:
		return now
	if style:
		now[doctype] = style
	else:
		now.pop(doctype, None)
	frappe.db.set_default(KEY, json.dumps(now, sort_keys=True))
	frappe.enqueue(
		"onedesk.one.avatars.fill",
		queue="long",
		job_id=f"one_avatars:{doctype}",
		deduplicate=True,
		enqueue_after_commit=True,
		doctype=doctype,
	)
	return now
