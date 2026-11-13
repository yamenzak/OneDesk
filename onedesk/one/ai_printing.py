"""OneAI on printing (one/agent.py lists these tools): the letter heads and
formats each kind of record prints with, and a change to them as a card."""

import re
from typing import Annotated

import frappe
from frappe import _


def workspace_printing(
	doctype: Annotated[str, "A kind of record, such as Sales Invoice, to also read its formats and default."]
	| None = None,
) -> dict:
	"""How the workspace's documents look on paper, for its administrators:
	its letter heads (which is the default, which are off, and each one's header
	and footer as they are now: the preset each is drawn from and what it shows,
	or the HTML or picture it was written as), the presets to choose from, the
	logo Workspace > General keeps, the print formats the workspace made, and for
	a kind of record the formats it may print with and the one it prints with
	unless another is chosen. Read it before suggesting a change."""
	from onedesk.one import control, roles
	from onedesk.one_studio import letter_heads, printing

	if not roles.administers():
		return {"error": "Only a workspace administrator sees how documents are printed."}
	try:
		company = control._company()
		said = {
			"letter_heads": [
				{
					**{key: one.get(key) for key in ("name", "is_default", "disabled", "standard")},
					"header": _letter_head_part(one, "header"),
					"footer": _letter_head_part(one, "footer"),
				}
				for one in printing.letter_heads()
			],
			"presets": {
				"header": {key: str(label) for key, label in letter_heads.PRESETS.items()},
				"footer": {
					**{key: str(label) for key, label in letter_heads.FEET.items()},
					"none": "None",
				},
				"header_shows": list(letter_heads.SHOWN),
				"footer_shows": [*letter_heads.FOOT_SHOWN, *letter_heads.SHOWN],
			},
			"company_logo": company.company_logo if company else None,
			"company": _on_documents(company),
			"workspace_formats": printing.formats(),
		}
		if doctype:
			printing._doctype(doctype)
			said["doctype"] = doctype
			said["default_format"] = frappe.get_meta(doctype).default_print_format
			said["formats"] = frappe.get_all(
				"Print Format",
				filters={"doc_type": doctype, "disabled": 0},
				fields=["name", "standard", "print_format_builder_beta as made_in_the_builder"],
				order_by="name asc",
			)
		return said
	except frappe.ValidationError as e:
		frappe.clear_last_message()
		return {"error": str(e)}


INLINE_PICTURE = re.compile(r'src="data:image/[^"]+"')


def _letter_head_part(one: dict, part: str) -> dict | None:
	"""A letter head's header or footer as it is now: the preset it is drawn from
	and its settings, or the HTML or picture it was written as. None for a
	letter head with no footer."""
	from onedesk.one_studio import letter_heads

	top = part == "header"
	drawn = one.get("one_top" if top else "one_foot")
	if drawn:
		said = letter_heads.settings(drawn) if top else letter_heads.foot_settings(drawn)
		presets = letter_heads.PRESETS if top else letter_heads.FEET
		return {"drawn_from": said["preset"], "called": str(presets[said["preset"]]), "settings": said}
	source = one.get("source" if top else "footer_source") or "Image"
	html = one.get("content" if top else "footer")
	picture = one.get("image" if top else "footer_image")
	if source == "HTML" and (html or "").strip():
		return {"written_in": "HTML", "html": INLINE_PICTURE.sub('src="[inline picture]"', html)[:4000]}
	if picture:
		return {"picture": picture}
	return None


def change_printing(
	doctype: Annotated[str, "The kind of record whose default format changes, such as Sales Invoice."]
	| None = None,
	default_format: Annotated[
		str, "The format that kind prints with unless another is chosen: one of its formats."
	]
	| None = None,
	letter_head: Annotated[
		dict,
		"A letter head to make or change: {name} of an existing one (read workspace_printing first: it "
		"gives each one's header and footer as they are now), or {new_name} for a new one. The header: "
		"{preset}, one of workspace_printing's header presets, drawn from the company's details in "
		"Workspace > General, with {show} (a list of its header_shows), {logo_height} in pixels, {align} "
		"for Logo Only, and {line} 0 to leave out the line in the Brand Colour under it; this is what to "
		"suggest first. The footer: {foot}, an object with {preset} (one of its footer presets, or none "
		"for no footer), {show} (its footer_shows, logo included), {note} (a short line of their own, "
		"such as a thank-you; empty for none) and {line}. On a letter head that is there, give only what "
		"changes: the rest stays as it is, and the preset may be left out when its header or footer is "
		"already drawn from one. Or {logo}, 'company' for the logo Workspace > General keeps or a file "
		"URL the workspace already has; or {top_html} and {foot_html}, the header and footer written in "
		"plain HTML with inline styles (no template tags, no scripts, pictures only from this workspace's "
		"files), from the company's details workspace_printing gives, where [icon:phone] (any Lucide "
		"name: map-pin, mail, globe, receipt...) draws that icon in the Brand Colour. The page number is "
		"the print format's own, never the footer's. {default} true to make it the one printed unless "
		"another is chosen; {off} true to turn it off.",
	]
	| None = None,
	why: Annotated[str, "In a sentence, what the change is for."] | None = None,
) -> dict:
	"""Suggest how documents are printed, as a card a workspace administrator
	approves: which format a kind of record prints with by default, a letter
	head, made from the workspace's logo or designed in HTML from its details,
	or which letter head is the default. A format's own layout is
	design_print_format. Read workspace_printing first. The card shows the
	page before it is approved; nothing changes until they approve it.
	Workspace administrators only."""
	from onedesk.one import control, roles
	from onedesk.one_ai import proposals
	from onedesk.one_studio import letter_heads, print_html, printing

	if not roles.administers():
		return {"error": "Only a workspace administrator changes how documents are printed."}
	summary, head = [], None
	try:
		if default_format:
			if not doctype:
				return {"error": "Say which kind of record prints with that format."}
			printing._doctype(doctype)
			if frappe.db.get_value("Print Format", default_format, "doc_type") != doctype:
				return {
					"error": f"{default_format} is not a format of {doctype}; read workspace_printing for its formats."
				}
			was = frappe.get_meta(doctype).default_print_format
			if was != default_format:
				summary.append(
					{
						"label": _("Prints With"),
						"value": _("{0} (was {1})").format(default_format, was or _("Standard")),
					}
				)
			else:
				default_format = None
		if letter_head:
			name = (letter_head.get("name") or "").strip() or None
			if name and not frappe.db.exists("Letter Head", name):
				return {"error": f"There is no letter head {name}; read workspace_printing for them."}
			logo = letter_head.get("logo")
			if logo == "company":
				company = control._company()
				logo = company.company_logo if company else None
				if not logo:
					return {"error": "Workspace > General has no logo yet; ask them to add one there first."}
			top, foot = letter_head.get("top_html"), letter_head.get("foot_html")
			was = (
				frappe.db.get_value("Letter Head", name, ["one_top", "one_foot"], as_dict=True)
				if name
				else frappe._dict()
			)
			top_said = {key: letter_head[key] for key in letter_heads.TOP_KEYS if key in letter_head}
			preset = top_said.get("preset")
			if preset and preset not in letter_heads.PRESETS:
				return {
					"error": f"{preset} is not a header preset; they are {', '.join(letter_heads.PRESETS)}."
				}
			if top_said and not preset and not was.one_top:
				return {
					"error": "Its header is not drawn from a preset (it is a picture or written by hand); "
					"give a preset to draw one, or top_html to write it."
				}
			foot_said = letter_head.get("foot") if isinstance(letter_head.get("foot"), dict) else None
			no_foot = bool(foot_said) and foot_said.get("preset") == "none"
			if foot_said and not no_foot:
				if foot_said.get("preset") and foot_said["preset"] not in letter_heads.FEET:
					return {
						"error": f"The footer's preset is one of {', '.join(letter_heads.FEET)}, or none."
					}
				if not foot_said.get("preset") and not was.one_foot:
					return {
						"error": "Its footer is not drawn from a preset; give a preset to draw one, "
						"or foot_html to write it."
					}
			if not name and not (letter_head.get("new_name") and (logo or top or preset)):
				return {"error": "A new letter head needs new_name, and a preset, a logo or top_html."}
			head = {"name": name}
			if not name:
				head["letter_head_name"] = letter_head["new_name"].strip()
				summary.append({"label": _("New Letter Head"), "value": head["letter_head_name"]})
			if top_said:
				before = letter_heads.settings(was.one_top) if was.one_top else None
				after = letter_heads.settings({**(before or {}), **top_said})
				if after != before:
					head["one_top"] = after
					head["source"] = "HTML"
					head["content"] = letter_heads.draw(after)
					summary.append(
						{"label": _("Header"), "value": str(letter_heads.PRESETS[after["preset"]])}
					)
			if logo and not top and not top_said:
				head["source"] = "Image"
				head["image"] = logo
				summary.append({"label": _("Logo"), "value": logo.rsplit("/", 1)[-1].split("?")[0]})
			if top:
				head["source"] = "HTML"
				head["content"] = print_html.letter_head_html(top, _("Header"))
				summary.append({"label": _("Header"), "value": _("Designed in HTML")})
			if no_foot and (
				was.one_foot or name is None or frappe.db.get_value("Letter Head", name, "footer")
			):
				head["one_foot"] = None
				head["footer_source"] = "HTML"
				head["footer"] = ""
				summary.append({"label": _("Footer"), "value": _("None")})
			elif foot_said and not no_foot:
				before = letter_heads.foot_settings(was.one_foot) if was.one_foot else None
				after = letter_heads.foot_settings({**(before or {}), **foot_said})
				if after != before:
					head["one_foot"] = after
					head["footer_source"] = "HTML"
					head["footer"] = letter_heads.draw_foot(after)
					summary.append({"label": _("Footer"), "value": str(letter_heads.FEET[after["preset"]])})
			if foot and not foot_said:
				head["footer_source"] = "HTML"
				head["footer"] = print_html.letter_head_html(foot, _("Footer"))
				summary.append({"label": _("Footer"), "value": _("Designed in HTML")})
			if letter_head.get("default") is not None:
				head["is_default"] = 1 if letter_head["default"] else 0
				summary.append({"label": _("Default"), "value": _("Yes") if head["is_default"] else _("No")})
			if letter_head.get("off") is not None:
				head["disabled"] = 1 if letter_head["off"] else 0
				summary.append({"label": _("Off"), "value": _("Yes") if head["disabled"] else _("No")})
	except frappe.ValidationError as e:
		frappe.clear_last_message()
		return {"error": str(e)}
	if not summary:
		return {
			"error": "That is how it prints already, so there is nothing to change. Say it is right as it is."
		}
	return {
		"proposal": proposals.propose(
			"Printing",
			doctype if default_format else "Letter Head",
			changes={
				"state": printing.state(doctype if default_format else None),
				"default_format": default_format,
				"letter_head": head,
				"summary": summary,
			},
			why=why,
		),
		"state": "Proposed",
		"next": "Tell them See the Page on the card shows it before they approve it, that it applies once "
		"they do, and that Setup › Printing shows it.",
	}


def _on_documents(company) -> dict:
	"""The company as a printed page shows it (Workspace > General > Contact and Branding)."""
	from onedesk.one import control

	if not company:
		return {}
	address = control._company_address(company)
	return {
		"name": company.company_name,
		"phone": company.phone_no,
		"email": company.email,
		"website": company.website,
		"address": [
			one
			for one in (
				*(address.get(key) for key in control.ADDRESS),
				company.country,
			)
			if one
		]
		if address
		else [company.country],
	}
