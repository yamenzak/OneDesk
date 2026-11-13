"""A presentation's master: what every slide draws underneath its own, kept
as a second Presentation of one slide whose `master_of` is the one it
belongs to (AGENTS.md, Master and layouts)."""

import json
import re
import uuid
from typing import Annotated

import frappe
from frappe import _

FIELDS = ("number", "date")


def of(name: str) -> str | None:
	"""The master of a presentation, if it has one."""
	return frappe.db.get_value("Presentation", {"master_of": name}, "name")


def elements(name: str) -> list[dict]:
	"""What the master of a presentation draws, as kept; none if it has none."""
	master = of(name)
	if not master:
		return []
	kept = frappe.db.get_value("Presentation Slide", {"parent": master, "parenttype": "Presentation"}, "elements", order_by="idx asc")
	try:
		drawn = json.loads(kept or "[]")
	except ValueError:
		return []
	return [one for one in drawn if isinstance(one, dict) and not one.get("hidden")]


#: How wide a date field is drawn at least.
DATE_WIDE = 140


def filled(drawn: list[dict], number: int, today: str) -> list[dict]:
	"""The master's elements for one slide: its own ids, so they never meet the
	slide's, and each field's words put in. Pure."""
	out = []
	for one in drawn:
		one = {**one, "id": f"master-{one.get('id')}"}
		if one.get("field") in FIELDS and isinstance(one.get("content"), str):
			one["content"] = _worded(one["content"], str(number) if one["field"] == "number" else today)
		if one.get("field") == "date" and (one.get("width") or 0) < DATE_WIDE:
			# a date is wider than the box it was first given, in some formats and faces
			one["width"] = DATE_WIDE
		out.append(one)
	return out


def _worded(content: str, words: str) -> str:
	"""A text's first run of words made `words`, the rest of them dropped, its
	look kept. Pure."""
	from frappe.utils import escape_html

	done = []

	def one(match):
		if done:
			return "><"
		done.append(True)
		return f">{escape_html(words)}<"

	worded = re.sub(r">[^<]+<", one, content)
	return worded if done else f"<p>{escape_html(words)}</p>"


def under(name: str, slides: list[dict]) -> list[dict]:
	"""Each slide with the master's elements put underneath its own, for what
	draws slides without the editor (the TV, PowerPoint). `slides` are rows as
	kept, elements still JSON."""
	from frappe.utils import formatdate, nowdate

	drawn = elements(name)
	if not drawn:
		return slides
	today = formatdate(nowdate())
	out = []
	for number, row in enumerate(slides, start=1):
		if row.get("hide_master"):
			out.append(row)
			continue
		own = json.loads(row.get("elements") or "[]") if isinstance(row.get("elements"), str) else row.get("elements") or []
		out.append({**row, "elements": json.dumps(filled(drawn, number, today) + own)})
	return out


@frappe.whitelist(methods=["POST"])
def edit(name: Annotated[str, "The presentation whose master is opened."]) -> str:
	"""The presentation's master, made blank the first time: its name, which
	the editor opens."""
	from onedesk.one_deck import api

	api._may(name, "write")
	if frappe.db.get_value(api.PRESENTATION, name, "master_of"):
		frappe.throw(_("Could not open a master: this presentation is already one."))
	made = of(name)
	if made:
		return made
	width, height = api.frame(name)
	doc = frappe.get_doc(
		{
			"doctype": api.PRESENTATION,
			"title": _("Master"),
			"master_of": name,
			"theme": frappe.db.get_value(api.PRESENTATION, name, "theme"),
			"width": width,
			"height": height,
			"slides": [{"client_id": str(uuid.uuid4()), "background": "", "elements": "[]"}],
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc.name


def copy(source: str, to: str) -> None:
	"""A copy of one presentation's master for another, with copies of its pictures."""
	from onedesk.one_deck import api

	master = of(source)
	if not master:
		return
	made = frappe.copy_doc(frappe.get_doc(api.PRESENTATION, master))
	made.master_of = to
	made.file = None
	made.is_template = 0
	made.flags.ignore_permissions = True
	made.insert()
	for row in made.slides:
		drawn = json.loads(row.elements or "[]")
		for one in drawn:
			api._adopted(made.name, one)
		row.elements = json.dumps(drawn)
	made.save(ignore_permissions=True)


def forget(name: str) -> None:
	"""A presentation's master goes with it, and its pictures."""
	from onedesk.one_deck import api, versions

	master = of(name)
	if not master:
		return
	for held in frappe.get_all("File", filters={"attached_to_doctype": api.PRESENTATION, "attached_to_name": master}, pluck="name"):
		frappe.delete_doc("File", held, ignore_permissions=True)
	versions.forget(master)
	frappe.delete_doc(api.PRESENTATION, master, ignore_permissions=True, force=True)
