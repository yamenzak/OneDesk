"""What OneAI makes for OneDisplay from a sentence (one_display/AGENTS.md,
stage 6): a picture for a slide, a designed slide, a widget of your own. Each
is something to look at and change before it is used; nothing here puts
anything on a screen by itself."""

import base64
import re
from typing import Annotated

import frappe
from frappe import _

from onedesk.one import apps

FENCE = re.compile(r"^```[a-zA-Z]*\s*|\s*```$")
EXTENSIONS = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}


def _may(doctype: str) -> None:
	frappe.has_permission(doctype, "write", throw=True)
	apps.refuse_ai()


def _brand() -> str:
	company = frappe.db.get_default("company")
	colour = frappe.db.get_value("Company", company, "one_brand_colour") if company else None
	name = frappe.db.get_value("Company", company, "company_name") if company else None
	return f"The business is {name or 'the workspace'}; its brand colour is {colour or '#2563eb'}."


@frappe.whitelist(methods=["POST"])
def picture(description: Annotated[str, "What the picture shows."]) -> str:
	"""A picture for a slide, kept as a public file: its address."""
	_may("Slide Playlist")
	from onedesk.one_ai import run

	said = run.make("display_picture", description.strip()[:2000], reference="OneDisplay picture")
	if not said.get("data"):
		frappe.throw(_("OneAI could not make the picture. Try again."))
	extension = EXTENSIONS.get((said.get("mime") or "").split(";")[0], "png")
	saved = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"slide-{frappe.generate_hash(length=8)}.{extension}",
			"content": base64.b64decode(said["data"]),
			"is_private": 0,
			"folder": "Home",
		}
	).insert()
	return saved.file_url


def _code(said: str) -> str:
	return FENCE.sub("", (said or "").strip()).strip()


@frappe.whitelist(methods=["POST"])
def design(
	description: Annotated[str, "What the slide says and looks like."],
	orientation: Annotated[str, "Landscape or Portrait."] = "Landscape",
) -> str:
	"""A slide as HTML and CSS, drawn at the screen's size."""
	_may("Slide Playlist")
	from onedesk.one_ai import run

	said = run.once("display_design", f"{_brand()}\nOrientation: {orientation}.\n\n{description.strip()[:4000]}", reference="OneDisplay design")
	html = _code(said)
	if not html:
		frappe.throw(_("OneAI could not design the slide. Try again."))
	return html


@frappe.whitelist(methods=["POST"])
def widget(
	description: Annotated[str, "What the widget shows and does."],
	rows: Annotated[str | None, "A sample of the rows it will be given, as JSON."] = None,
) -> str:
	"""A custom widget's code, for a widget of kind Custom."""
	_may("Widget Collection")
	from onedesk.one_ai import run

	sample = f"\nIts rows look like this: {rows[:2000]}" if rows else ""
	said = run.once("display_widget", f"{_brand()}{sample}\n\n{description.strip()[:4000]}", reference="OneDisplay widget")
	code = _code(said)
	if not code:
		frappe.throw(_("OneAI could not write the widget. Try again."))
	return code
