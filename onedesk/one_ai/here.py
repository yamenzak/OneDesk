"""Where the reader is, for the places a module does not answer for itself: a
report, a dashboard, a space's home. And every place the rail opens, as the
browser tells OneAI it is there (public/js/oneai.js, `where`), with what
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
	the same fields `where` in public/js/oneai.js sends for that route."""
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
	from onedesk.one_ai.chat import _page

	missed = []
	for place in places():
		said = _page(place["sent"]) if place["sent"] else ""
		if not said or said == title_only(place["sent"]):
			missed.append({**place, "said": said})
	return missed
