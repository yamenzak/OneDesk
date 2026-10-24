"""A mailbox's signature, drawn from a preset like a letter head's top: the
person who writes from it (their name, job and numbers) and the company
(its logo, colour and details), showing what was ticked. Drawn as tables
with inline styles, since that is what every mail client keeps. A
signature written by hand is Custom and is never redrawn."""

import json
import re

import frappe
from frappe import _lt
from frappe.utils import escape_html, strip_html_tags

from onedesk.one import letter_heads

PRESETS = {
	"simple": _lt("Simple"),
	"beside": _lt("Logo Beside"),
	"above": _lt("Logo Above"),
	"accent": _lt("Accent"),
	"line": _lt("One Line"),
	"tinted": _lt("Tinted"),
}

SHOWS = {
	"company": _lt("Company Name"),
	"title": _lt("Job Title"),
	"phone": _lt("Phone"),
	"mobile": _lt("Mobile"),
	"email": _lt("Email"),
	"website": _lt("Website"),
	"address": _lt("Address"),
	"logo": _lt("Logo"),
}

SHOWN = ("company", "title", "phone", "email", "website", "logo")

WITH_LOGO = ("beside", "above")

FONT = "font-family:Arial,Helvetica,sans-serif;"
LOGO = 44


def person_of(account: str) -> str | None:
	"""Whose name a mailbox signs with: a shared mailbox signs as the company,
	anyone else's as its one holder."""
	if frappe.db.get_value("Email Account", account, "one_shared"):
		return None
	held = frappe.get_all("User Email", filters={"email_account": account}, pluck="parent", limit=2)
	return held[0] if len(held) == 1 else None


def details(account: str) -> dict:
	"""What a signature can show, from the person, the mailbox and the company."""
	company = letter_heads.company()
	email = frappe.db.get_value("Email Account", account, "email_id")
	out = {
		"company": company.get("name") or "",
		"colour": company.get("colour") or letter_heads.INK,
		"logo": company.get("logo") or "",
		"website": company.get("website") or "",
		"address": ", ".join(company.get("address") or []),
		"phone": company.get("phone") or "",
		"email": email or "",
		"name": "",
		"title": "",
		"mobile": "",
	}
	user = person_of(account)
	if user:
		held = frappe.db.get_value("User", user, ["full_name", "phone", "mobile_no"], as_dict=True) or {}
		out["name"] = held.get("full_name") or ""
		out["mobile"] = held.get("mobile_no") or ""
		out["phone"] = held.get("phone") or out["phone"]
		if frappe.db.table_exists("Employee"):
			employee = frappe.db.get_value(
				"Employee",
				{"user_id": user, "status": "Active"},
				["designation", "cell_number"],
				as_dict=True,
			)
			if employee:
				out["title"] = employee.designation or ""
				out["mobile"] = out["mobile"] or employee.cell_number or ""
	return out


def draw(preset: str, said: dict, shown: set | list) -> str:
	"""A signature's HTML. Pure apart from escaping."""
	shown = set(shown)
	e = lambda key: escape_html(str(said.get(key) or ""))  # noqa: E731
	colour = said.get("colour") or letter_heads.INK
	name = e("name") or e("company")
	company = e("company") if said.get("name") and "company" in shown else ""
	title = e("title") if "title" in shown else ""
	reach = [
		e(key) if key != "website" else e(key).removeprefix("https://").removeprefix("http://")
		for key in ("phone", "mobile", "email", "website")
		if key in shown and said.get(key)
	]
	address = e("address") if "address" in shown else ""
	logo = (
		f'<img src="{e("logo")}" alt="{e("company")}" height="{LOGO}" style="height:{LOGO}px;width:auto;display:block;border:0">'
		if "logo" in shown and said.get("logo")
		else ""
	)
	small = f"{FONT}font-size:12px;line-height:1.5;color:{letter_heads.MUTED};"
	big = f"{FONT}font-size:14px;line-height:1.4;font-weight:bold;color:{letter_heads.INK};"
	dot = '<span style="color:#d1d5db;padding:0 5px">·</span>'
	logo_top = f'<div style="margin-bottom:10px">{logo}</div>' if logo else ""
	logo_under = f'<div style="margin-top:8px">{logo}</div>' if logo else ""

	def block(name_style: str = big) -> str:
		lines = [f'<div style="{name_style}">{name}</div>']
		if title or company:
			lines.append(f'<div style="{small}">{" · ".join(one for one in (title, company) if one)}</div>')
		if reach:
			lines.append(f'<div style="{small}">{dot.join(reach)}</div>')
		if address:
			lines.append(f'<div style="{small}">{address}</div>')
		return "".join(lines)

	if preset == "line":
		parts = [
			f'<b style="color:{letter_heads.INK}">{name}</b>',
			*(one for one in (title, company) if one),
			*reach,
		]
		return f'<div style="{small}">{dot.join(parts)}</div>'
	if preset == "beside" and logo:
		return (
			'<table cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse"><tr>'
			f'<td style="padding-right:14px;vertical-align:middle">{logo}</td>'
			f'<td style="border-left:2px solid {colour};padding-left:14px;vertical-align:middle">{block()}</td>'
			"</tr></table>"
		)
	if preset == "above":
		return f"<div>{logo_top}{block()}</div>"
	if preset == "accent":
		return (
			f'<div style="border-left:3px solid {colour};padding-left:12px">'
			f"{block(big.replace(letter_heads.INK, colour))}{logo_under}</div>"
		)
	if preset == "tinted":
		return (
			'<table cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse"><tr>'
			f'<td style="background:{letter_heads.tint(colour, 0.08)};border-radius:8px;padding:12px 16px">'
			f"{logo_top}{block()}</td></tr></table>"
		)
	return block()


def written(html: str | None) -> str:
	"""A signature with something in it, or nothing: an emptied editor
	leaves its own markup behind."""
	html = html or ""
	return html if strip_html_tags(html).strip() or "<img" in html else ""


def shows_of(raw) -> list[str]:
	"""What a signature shows, from a list or its JSON; what most show when unsaid."""
	said = raw
	if isinstance(raw, str):
		try:
			said = json.loads(raw) if raw else None
		except ValueError:
			said = None
	return [one for one in (said if isinstance(said, list) else SHOWN) if one in SHOWS]


def sender_name_for(account: str | None, sender: str | None) -> str | None:
	"""The name a mailbox sends under, if it has one set: what people see
	beside its address. Without one, mail goes under the writer's name."""
	if not account and sender:
		from email.utils import parseaddr

		account = frappe.db.get_value("Email Account", {"email_id": parseaddr(sender)[1]}, "name")
	if not account:
		return None
	return (frappe.db.get_value("Email Account", account, "one_sender_name") or "").strip() or None


def default_sender_name(account: str) -> str:
	"""Who mail from a mailbox goes out as with no Sender Name: the person an
	address belongs to, or for a shared one, whoever writes."""
	user = person_of(account)
	return frappe.utils.get_fullname(user) if user else ""


@frappe.whitelist()
def presets_of(account: str, show: str | list | None = None) -> dict:
	"""Every preset drawn for this mailbox, the one chosen, and what it shows."""
	from onedesk.one_mail import holders

	holders.sees(account)
	held = frappe.db.get_value(
		"Email Account", account, ["signature", "one_signature_preset", "one_signature_show"], as_dict=True
	)
	shown = shows_of(show if show is not None else held.one_signature_show)
	said = details(account)
	return {
		"presets": [
			{"preset": key, "label": str(label), "html": draw(key, said, shown)}
			for key, label in PRESETS.items()
			if key not in WITH_LOGO or said.get("logo")
		],
		"shows": [
			{
				"key": key,
				"label": str(label),
				"has": bool(said.get(key)) and (key != "company" or bool(said.get("name"))),
			}
			for key, label in SHOWS.items()
		],
		"colour": said["colour"],
		"sender_name": frappe.db.get_value("Email Account", account, "one_sender_name") or "",
		"default_sender_name": default_sender_name(account),
		"preset": held.one_signature_preset or ("" if written(held.signature) else "simple"),
		"shown": shown,
		"signature": written(held.signature),
	}


@frappe.whitelist(methods=["POST"])
def set_preset(
	account: str,
	preset: str | None = None,
	show: str | list | None = None,
	signature: str | None = None,
	sender_name: str | None = None,
) -> None:
	"""Sign with a preset, drawn now, or with a signature written by hand
	(Custom, when `preset` is empty), and send under `sender_name` (empty for
	the default; left out, unchanged)."""
	from onedesk.one_mail import holders

	holders.manages(account)
	if preset and preset not in PRESETS:
		frappe.throw(frappe._("There is no such signature."))
	shown = shows_of(show)
	html = draw(preset, details(account), shown) if preset else written(signature)
	holders.set_signature(account, html)
	frappe.db.set_value(
		"Email Account",
		account,
		{
			"one_signature_preset": preset or None,
			"one_signature_show": json.dumps(shown),
			**({"one_sender_name": sender_name.strip() or None} if sender_name is not None else {}),
		},
		update_modified=False,
	)


def inline_logo(doc, method=None) -> None:
	"""Communication after_insert: the company's logo in a sent mail goes as
	part of the mail (frappe's `embed`, sent as an inline image) rather than
	a link to this site, which a mail client blocks until asked. A signature
	holds only the logo's path, so it is never a link to the wrong host. Only
	the copy about to be queued changes; the stored mail keeps the path,
	which is what One shows in Sent."""
	if doc.communication_medium != "Email" or doc.sent_or_received != "Sent" or not doc.content:
		return
	logo = letter_heads.company().get("logo")
	if not logo or not logo.startswith(("/files/", "/private/files/")) or logo not in doc.content:
		return
	doc.content = re.sub(rf'src="[^"]*{re.escape(logo)}"', f'embed="{logo[1:]}"', doc.content)
