"""Where the reader is, as the agent answering them is told it with their
question (`asked`): today, the workspace, the reader, the page or the field
they were in. For the places a module does not answer for itself: a
report, a dashboard, a space's home. And every place the rail opens, as the
browser tells OneAI it is there (public/js/one_ai/oneai.js, `where`), with what
OneAI is then told, so a place told only its title is found before somebody
asks "what am I looking at" on it. README, Where the reader is.
"""

import glob
import json
import os
import urllib.parse

import frappe

#: What a place with nothing to say about itself is told: only its title.
TITLE_ONLY = "The reader is on the {0} page."

#: Most charts, cards or links named for one place.
MOST = 12


def title_only(page: dict) -> str:
	return TITLE_ONLY.format(page.get("label") or page.get("page") or page.get("report") or page.get("dashboard") or page.get("view"))


def report(page: dict) -> str:
	"""A report on screen: what it reports on, the filters the reader set, and
	the tool that reads the rows they see."""
	name = (page.get("report") or "").strip()
	if not frappe.db.exists("Report", name) or not frappe.has_permission("Report", doc=name, ptype="read"):
		return title_only(page)
	held = frappe.db.get_value("Report", name, ["ref_doctype", "report_type"], as_dict=True)
	filters = {key: value for key, value in (page.get("filters") or {}).items() if value not in (None, "", [], 0)}
	narrowed = f", filtered to {json.dumps(filters, default=str)}" if filters else " with its own filters"
	return (
		f"The reader has the report {name} open, over {held.ref_doctype}{narrowed}. run_report with report "
		f'"{name}" and these filters answers with the rows and totals on their screen; another filter answers '
		"for something they are not looking at, so say which."
	)


def _chart(name: str) -> str | None:
	held = frappe.db.get_value(
		"Dashboard Chart",
		name,
		["chart_name", "chart_type", "document_type", "report_name", "based_on", "group_by_based_on", "timespan"],
		as_dict=True,
	)
	if not held:
		return None
	if held.chart_type == "Report" or held.report_name:
		return f"{held.chart_name} (from the report {held.report_name})"
	if not held.document_type:
		return held.chart_name
	if not frappe.has_permission(held.document_type, "read"):
		return None
	counted = "count" if held.chart_type in (None, "", "Count", "Group By") else held.chart_type.lower()
	by = f" by {held.group_by_based_on}" if held.chart_type == "Group By" and held.group_by_based_on else ""
	over = f", {held.timespan.lower()} by {held.based_on}" if held.based_on and held.timespan else ""
	return f"{held.chart_name} ({counted} of {held.document_type}{by}{over})"


def _card(name: str) -> str | None:
	held = frappe.db.get_value(
		"Number Card", name, ["label", "type", "document_type", "function", "aggregate_function_based_on", "report_name"], as_dict=True
	)
	if not held:
		return None
	if held.type == "Report":
		return f"{held.label} (from the report {held.report_name})"
	if held.type != "Document Type" or not held.document_type:
		return held.label
	if not frappe.has_permission(held.document_type, "read"):
		return None
	field = f" {held.aggregate_function_based_on}" if held.function != "Count" and held.aggregate_function_based_on else ""
	return f"{held.label} ({(held.function or 'Count').lower()} of {held.document_type}{field})"


def dashboard(page: dict) -> str:
	"""A dashboard on screen: each chart and number card, and what each counts."""
	name = (page.get("dashboard") or "").strip()
	if not frappe.db.exists("Dashboard", name):
		return title_only(page)
	doc = frappe.get_doc("Dashboard", name)
	charts = [one for one in (_chart(row.chart) for row in doc.charts[:MOST]) if one]
	cards = [one for one in (_card(row.card) for row in doc.cards[:MOST]) if one]
	if not charts and not cards:
		return title_only(page)
	shown = "; ".join(filter(None, [f"charts: {', '.join(charts)}" if charts else "", f"numbers: {', '.join(cards)}" if cards else ""]))
	return (
		f"The reader is on the {name} dashboard, which shows {shown}. count_records and list_records read what a "
		"chart or number over records shows, run_report what one from a report shows."
	)


def home(page: dict) -> str:
	"""A space's home that no module answers for: what it links to."""
	name = (page.get("workspace") or "").strip()
	if not frappe.db.exists("Workspace", name):
		return title_only(page)
	shortcuts = frappe.get_all("Workspace Shortcut", {"parent": name, "parenttype": "Workspace"}, pluck="label", order_by="idx")
	cards = frappe.get_all(
		"Workspace Link", {"parent": name, "parenttype": "Workspace", "type": "Link", "hidden": 0}, pluck="label", order_by="idx"
	)
	links = [one for one in shortcuts + cards if one]
	if not links:
		return title_only(page)
	title = frappe.db.get_value("Workspace", name, "title") or name
	return f"The reader is on {frappe._(title)}, a home that opens {', '.join(links[:MOST * 2])}."


def _doctype_of(slug: str) -> str | None:
	return frappe.db.get_value("DocType", {"name": slug.replace("-", " ")}, "name")


def sent(item: dict) -> dict | None:
	"""What the browser tells OneAI when the reader has opened this rail entry:
	the same fields `where` in public/js/one_ai/oneai.js sends for that route."""
	kind, to = item.get("link_type"), item.get("link_to")
	label = item.get("label") or to
	if kind == "DocType":
		return {"doctype": to, "name": "", "view": "List", "label": label}
	if kind == "Page":
		asked = frappe.parse_json(item.get("route_options") or "{}") or {}
		return {
			"page": to,
			"section": asked.get("section") or asked.get("view") or "",
			"record": asked.get("type") or asked.get("rule") or asked.get("name") or "",
			"view": "Page",
			"label": label,
		}
	if kind == "Report":
		held = frappe.db.get_value("Report", to, ["report_type", "ref_doctype"], as_dict=True)
		if held and held.report_type == "Report Builder":
			return {"doctype": held.ref_doctype, "name": "", "view": "Report", "label": label}
		return {"report": to, "view": "Report", "label": label}
	if kind == "Dashboard":
		return {"dashboard": to, "view": "Dashboard", "label": label}
	if kind == "Workspace":
		return {"workspace": to, "view": "Workspace", "label": label}
	if kind == "URL":
		url = urllib.parse.urlparse(item.get("url") or "")
		parts = [one for one in url.path.split("/") if one][1:]
		asked = dict(urllib.parse.parse_qsl(url.query))
		if asked.get("center"):
			# A module's ControlCenter is told as the module's own page
			# (one_interface/centre.js `activate`).
			centre = asked["center"] if asked["center"] != "settings" else (asked.get("module") or "One").lower()
			return {"page": centre, "section": asked.get("at") or "", "record": asked.get("record") or "", "view": "Page", "label": label}
		if not parts:
			return None
		if frappe.db.exists("Page", parts[0]):
			return {
				"page": parts[0],
				"section": asked.get("section") or asked.get("view") or "",
				"record": asked.get("type") or asked.get("name") or (parts[1] if len(parts) > 1 else ""),
				"view": "Page",
				"label": label,
			}
		doctype = _doctype_of(parts[0])
		if doctype:
			view = parts[2].title() if len(parts) > 2 and parts[1] == "view" else "List"
			return {"doctype": doctype, "name": "", "view": view, "label": label}
	return None


def places() -> list[dict]:
	"""Every entry on every space's rail, and every desk page One ships."""
	app = frappe.get_app_path("onedesk")
	found = []
	for path in sorted(glob.glob(os.path.join(app, "*", "sidebar", "*", "*.json"))):
		space = os.path.basename(path)[:-5]
		with open(path, encoding="utf-8") as held:
			items = json.load(held).get("items") or []
		for item in items:
			if item.get("type") == "Link":
				found.append({"space": space, "label": item.get("label"), "sent": sent(item)})
	for path in sorted(glob.glob(os.path.join(app, "*", "page", "*", "*.json"))):
		with open(path, encoding="utf-8") as held:
			name = json.load(held)["name"]
		found.append({"space": "page", "label": name, "sent": {"page": name, "view": "Page", "label": name}})
	return found


def untold() -> list[dict]:
	"""The places OneAI is told nothing about, or only their title, as the
	person signed in now."""
	missed = []
	for place in places():
		said = said_of(place["sent"]) if place["sent"] else ""
		if not said or said == title_only(place["sent"]):
			missed.append({**place, "said": said})
	return missed


def asked(
	text: str, page: dict | str | None, attached: list | None = None, field: dict | None = None, who: str = ""
) -> list[dict]:
	"""The reader's turn, the page they were on, and what they dropped on it,
	after who is answering (`who`, one_ai/agents/talk.py).

	A field being written replaces the page: it already says which record, and
	"the reader is looking at X" beside "the reader is writing X's notes" is the
	same sentence twice.
	"""
	from onedesk.one_ai import files as carrying
	from onedesk.one_ai import memory, touch

	where = touch.told(field) if field else said_of(page)
	where = " ".join(
		one for one in (who, _today(), _workspace(), _reader(), where, memory.told(_doctype(page))) if one
	)
	turns = [{"role": "user", "text": where, "calls": [], "context": True}]
	about = _field_asked(page)
	if about:
		turns[0]["about"] = about
	turns.append(
		{
			"role": "user",
			"text": text,
			"calls": [],
			"files": carrying.described(attached or []),
		}
	)
	return turns


def _workspace() -> str:
	"""The facts about this workspace a question can turn on: whose it is, its
	money, its clock — and whatever a module adds through `one_ai_workspace`,
	OneHR's weekly offs among them. A model that did not know Friday is off here
	booked it as a working day."""
	company = frappe.defaults.get_global_default("company")
	currency = frappe.defaults.get_global_default("currency")
	zone = frappe.db.get_single_value("System Settings", "time_zone")
	said = [
		"This workspace"
		+ (f" is {company}'s" if company else "")
		+ (f"; its money is {currency}" if currency else "")
		+ (f"; its clock is {zone}" if zone else "")
		+ "."
	]
	for path in frappe.get_hooks("one_ai_workspace"):
		one = frappe.get_attr(path)()
		if one:
			said.append(one)
	return " ".join(said)


def _doctype(page: dict | str | None) -> str | None:
	if isinstance(page, str):
		page = frappe.parse_json(page) if page.strip() else None
	if not isinstance(page, dict):
		return None
	return (page.get("doctype") or "").strip() or None


def _reader() -> str:
	"""Who is asking, so "my" and "me" are somebody.

	Without it a model asked for "my leave" filters on a field it invents with
	the value "me". A module that knows more about the reader — OneHR, their
	employee record — says it through the `one_ai_reader` hook.
	"""
	user = frappe.session.user
	said = [f"The reader is {frappe.utils.get_fullname(user)} ({user})."]
	language = frappe.db.get_value("User", user, "language") or frappe.db.get_single_value(
		"System Settings", "language"
	)
	if language and language != "en":
		called = frappe.db.get_value("Language", language, "language_name") or language
		said.append(f"They read {called}: answer in {called} unless they write in another language.")
	for path in frappe.get_hooks("one_ai_reader"):
		one = frappe.get_attr(path)()
		if one:
			said.append(one)
	return " ".join(said)


def _today() -> str:
	"""Today in the site's own timezone, weekday first, as a person says it."""
	today = frappe.utils.getdate(frappe.utils.nowdate())
	return f"Today is {today.strftime('%A')} {today.day} {today.strftime('%B %Y')} ({today.isoformat()})."


def said_of(page: dict | str | None) -> str:
	"""Where the reader is, in one sentence, from what the browser said it is.

	Nothing here is trusted: it names a record, and every tool that could then
	read that record checks the reader's own permission before it answers.
	"""
	if isinstance(page, str):
		page = frappe.parse_json(page) if page.strip() else None
	if not isinstance(page, dict):
		return ""

	doctype = (page.get("doctype") or "").strip()
	record = (page.get("name") or "").strip()
	view = (page.get("view") or "").strip()
	if doctype and record:
		said = f"The reader is looking at the {doctype} record {record}.{_brief(doctype, record)}{_fields_said(doctype)}"
		return said + _about(doctype, record, (page.get("field") or "").strip())
	if doctype:
		filters = page.get("filters")
		narrowed = f", narrowed to {json.dumps(filters)}" if filters else ""
		return f"The reader is looking at a {view or 'list'} of {doctype}{narrowed}.{_fields_said(doctype)}"
	if not any(page.get(key) for key in ("page", "workspace", "report", "dashboard")):
		return f"The reader is on the {view} page." if view else ""
	for path in frappe.get_hooks("one_ai_page"):
		said = frappe.get_attr(path)(page)
		if said:
			return said
	if page.get("report"):
		return report(page)
	if page.get("dashboard"):
		return dashboard(page)
	if page.get("workspace"):
		return home(page)
	return title_only(page)


def _brief(doctype: str, name: str) -> str:
	"""The record's main fields, as its card would show them, so a question
	about it starts from what it says — a CV's fit was being judged against a
	job opening the model had not read."""
	try:
		if not frappe.has_permission(doctype, "read", doc=name):
			return ""
		doc = frappe.get_doc(doctype, name)
		doc.apply_fieldlevel_read_permissions()
		row = doc.as_dict()
	except Exception:
		return ""
	from onedesk.one_ai import drawn as drawing

	drawn = drawing.card_of(doctype, row, most=BRIEF_FIELDS)
	said = "; ".join(f"{one['label']}: {one['value']}" for one in drawn["fields"] if one.get("value"))
	meta = frappe.get_meta(doctype)
	prose = next(
		(
			drawing.as_text(row.get(f.fieldname))
			for f in meta.fields
			if f.fieldtype in ("Text Editor", "Small Text", "Text", "Long Text")
			and not f.hidden
			and row.get(f.fieldname)
		),
		"",
	)
	title = drawn.get("title") if drawn.get("title") != name else ""
	parts = [f"“{title}”" if title else "", said, prose[:BRIEF_PROSE]]
	told = ". ".join(one.rstrip(".") for one in parts if one)
	return f" It says: {told[:BRIEF_SAID]}." if told else ""


BRIEF_SAID = 700
BRIEF_FIELDS = 8
BRIEF_PROSE = 300


def expects_edit(turns: list[dict]) -> str | None:
	"""A question asked from a field's own mark is answered with a change to
	it — or with "it is right as it is", which the edit refuses as no change."""
	newest = next((one for one in reversed(turns) if one.get("context")), {})
	return "edit_record" if newest.get("about") else None


def _field_asked(page) -> str | None:
	if isinstance(page, str):
		page = frappe.parse_json(page) if page.strip() else None
	return ((page or {}).get("field") or "").strip() or None if isinstance(page, dict) else None


def _about(doctype: str, record: str, fieldname: str) -> str:
	"""The one field a question is about, handed over with the question: what
	it is for, what it holds, and what it may hold. Sent when the panel is
	opened from a field, a setting say, whose question a small model otherwise
	answered from the field list alone — "no change suggested" for an empty
	template field with the obvious template sitting there."""
	if not fieldname:
		return ""
	from onedesk.one_ai import tools

	try:
		said = tools.about_field(doctype, fieldname, record)
	except Exception:
		return ""
	return f" The question is about this field: {json.dumps(said, default=str)}"


def _fields_said(doctype: str) -> str:
	"""The type's fields, told up front: a model that has them uses them, and
	one that has to ask for them first guesses instead — "due_date" on a ToDo
	whose field is "date"."""
	if not frappe.db.exists("DocType", doctype) or not frappe.has_permission(doctype, "read"):
		return ""
	from onedesk.one_ai.kind import fields_of

	return f" {doctype}'s fields: {', '.join(fields_of(frappe.get_meta(doctype), most=40))}."
