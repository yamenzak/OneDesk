"""OneAI sets up what a workspace keeps of its own: saved reports, dashboards,
reports by mail, levels, profiles, groups and what a person sees.

Each tool here checks what it was asked against the same rules the page does,
and writes a card (an `AI Proposal` of kind Setup) that does nothing until a
person approves it. Approving runs the page's own code (one/reports.py,
one/access.py) as whoever pressed Approve, so a card can do no more than they
could by hand. A card says in plain words what changes: a level's card names
every right it gives and takes away.

All of them run on Workspace Setup, the stronger model approvals and
automations run on.
"""

import hashlib
import json
from typing import Annotated

import frappe
from frappe import _
from frappe.model import no_value_fields
from frappe.utils import validate_email_address

from onedesk.one import access, reports, roles
from onedesk.one.customize import REFUSED_MODULES

#: Fields every record has, which a report may show and filter on.
STANDARD = ("name", "owner", "creation", "modified", "docstatus")

#: How a filter compares, as frappe takes it.
OPERATORS = ("=", "!=", ">", "<", ">=", "<=", "like", "not like", "in", "not in", "is")

#: A right as somebody would say it, and frappe's name for it.
RIGHT_WORDS = {
	"pick": "select",
	"select": "select",
	"read": "read",
	"see": "read",
	"open": "read",
	"edit": "write",
	"write": "write",
	"change": "write",
	"create": "create",
	"make": "create",
	"delete": "delete",
	"submit": "submit",
	"cancel": "cancel",
	"export": "export",
}

#: How a right is said on a card.
VERB = {
	"select": "pick",
	"read": "read",
	"write": "edit",
	"create": "create",
	"delete": "delete",
	"submit": "submit",
	"cancel": "cancel",
	"export": "export",
}

FREQUENCIES = ("Daily", "Weekdays", "Weekly", "Monthly")
DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
FORMATS = ("HTML", "XLSX", "CSV")
INTERVALS = ("Daily", "Weekly", "Monthly", "Quarterly", "Yearly")
TIMESPANS = ("Last Week", "Last Month", "Last Quarter", "Last Year")


class Mend(Exception):
	"""What the model is told to put right, in its own words."""


def _mend(tool: str, error: str) -> dict:
	return {"mend": tool, "error": error}


def _card(
	what: str, doctype: str, payload: dict, title: str, summary: list, route: list, why: str | None
) -> dict:
	from onedesk.one_ai import proposals

	changes = {"what": what, **payload, "title": title, "summary": summary, "route": route}
	return {
		"proposal": proposals.propose("Setup", doctype, changes=changes, why=why),
		"state": "Proposed",
		"next": "Say in one sentence what approving it does. Nothing changes until they approve it.",
	}


def _kind(doctype: str):
	"""A kind of record the reader may read, and that is a record."""
	if not doctype or not frappe.db.exists("DocType", doctype):
		raise Mend(f"{doctype} is not a kind of record; describe_type gives one's fields.")
	meta = frappe.get_meta(doctype)
	if meta.istable or meta.issingle or meta.module in REFUSED_MODULES:
		raise Mend(f"{doctype} is not something a report or a chart is made of.")
	if not frappe.has_permission(doctype, "read"):
		raise Mend(f"The reader cannot open {doctype}, so nothing of it can be made for them.")
	return meta


def _field(meta, fieldname: str, numbers: bool = False, dates: bool = False):
	"""A field of a kind a report may show, filter, sum or chart over time."""
	if fieldname in STANDARD and not numbers:
		if dates and fieldname not in ("creation", "modified"):
			raise Mend(f"{fieldname} is not a date.")
		return fieldname
	df = meta.get_field(fieldname)
	if not df or df.hidden or df.permlevel or df.fieldtype in no_value_fields:
		raise Mend(f"{meta.name} has no field {fieldname} that can be shown; describe_type gives its fields.")
	if numbers and df.fieldtype not in ("Currency", "Float", "Int", "Percent"):
		raise Mend(f"{fieldname} is not a number, so it cannot be added up.")
	if dates and df.fieldtype not in ("Date", "Datetime"):
		raise Mend(f"{fieldname} is not a date.")
	return df.fieldname


def _filters(meta, filters: list | None) -> list:
	"""Filters as frappe keeps them: [kind, field, operator, value, False]."""
	said = []
	for one in filters or []:
		if isinstance(one, dict):
			one = [one.get("field"), one.get("operator") or "=", one.get("value")]
		if not isinstance(one, (list, tuple)) or len(one) < 3:
			raise Mend("A filter is [field, operator, value].")
		field, operator, value = one[-3], str(one[-2]).lower(), one[-1]
		if operator not in OPERATORS:
			raise Mend(f"{operator} is not an operator; use one of {', '.join(OPERATORS)}.")
		said.append([meta.name, _field(meta, field), operator, value, False])
	return said


def _said_filters(meta, filters: list) -> str:
	def label(field):
		df = meta.get_field(field)
		return _(df.label) if df else field

	return "; ".join(f"{label(one[1])} {one[2]} {one[3]}" for one in filters) or _("None")


def _measured(meta, measure: str, field: str | None) -> str:
	"""How a chart or card counts, as somebody would say it."""
	if measure == "count":
		return _("Count of {0}").format(_(meta.name))
	label = _(meta.get_field(field).label) if meta.get_field(field) else field
	word = _("Total of {0}") if measure == "sum" else _("Average of {0}")
	return word.format(label) + " " + _("on {0}").format(_(meta.name))


def _place(show_in: str | None, everybody: bool) -> dict | None:
	"""Where a report or dashboard is to be listed, as Show In would set it."""
	if everybody and not roles.administers():
		raise Mend("Only a workspace administrator shows something to everybody; leave everybody false.")
	if not show_in:
		return None
	for one in reports.places():
		if show_in in (one["label"], one["module"]):
			return {"module": one["module"], "label": one["label"], "everybody": int(bool(everybody))}
	raise Mend(
		f"{show_in} is not an app it can be shown in; one of {', '.join(p['label'] for p in reports.places())}."
	)


def _person(who: str) -> str:
	"""A person of the workspace, by address or by name."""
	from onedesk.one.settings import NOT_PEOPLE

	found = frappe.get_all(
		"User",
		filters={"user_type": "System User", "enabled": 1, "name": ["not in", NOT_PEOPLE]},
		or_filters={"name": who, "full_name": who, "first_name": who},
		pluck="name",
	)
	if len(found) != 1:
		raise Mend(f"{who} is {'nobody' if not found else 'more than one person'} here; give their address.")
	return found[0]


# ------------------------------------------------------------------ the tools


def suggest_saved_report(
	doctype: Annotated[str, "The kind of record the report lists, such as Sales Invoice."],
	name: Annotated[str, "What it is called, such as Unpaid Invoices."],
	columns: Annotated[list[str], "Field names to show, in order; describe_type gives them."],
	filters: Annotated[list, 'Each as [field, operator, value], such as ["outstanding_amount", ">", 0].']
	| None = None,
	sort_by: Annotated[str, "A field to sort by."] | None = None,
	descending: Annotated[bool, "Largest or newest first."] = True,
	totals: Annotated[bool, "A totals row under the numbers."] = False,
	show_in: Annotated[
		str, "The app whose sidebar lists it, such as OneBook; left out, the app its list is in."
	]
	| None = None,
	everybody: Annotated[
		bool, "In everybody's sidebar there, rather than the reader's; administrators only."
	] = False,
	why: Annotated[str, "In a sentence, what it is for."] | None = None,
) -> dict:
	"""Suggest a saved report: a list's Report view with its columns, filters
	and sorting, saved under a name and listed under Saved Reports in an app.
	Read describe_type for the kind first. Nothing is saved until the reader
	approves the card."""
	try:
		meta = _kind(doctype)
		name = (name or "").strip()
		if not name or frappe.db.exists("Report", name):
			raise Mend(f"Give the report a name nothing else has{'; ' + name + ' is taken' if name else ''}.")
		shown = [_field(meta, one) for one in (columns or [])[:20]]
		if not shown:
			raise Mend("Give at least one column.")
		kept = _filters(meta, filters)
		order = _field(meta, sort_by) if sort_by else "modified"
		place = _place(show_in, everybody)
	except Mend as e:
		return _mend("suggest_saved_report", str(e))
	settings = {
		"fields": [[one, doctype] for one in (["name"] + [c for c in shown if c != "name"])],
		"filters": kept,
		"order_by": f"`tab{doctype}`.`{order}` {'desc' if descending else 'asc'}",
		"add_totals_row": int(bool(totals)),
		"page_length": 20,
		"column_widths": {},
		"group_by": None,
	}
	label = lambda f: _(meta.get_field(f).label) if meta.get_field(f) else f  # noqa: E731
	df = meta.get_field(order)
	dated = order in ("creation", "modified") or (df and df.fieldtype in ("Date", "Datetime"))
	numbered = df and df.fieldtype in ("Currency", "Float", "Int", "Percent")
	if dated:
		way = _("newest first") if descending else _("oldest first")
	elif numbered:
		way = _("largest first") if descending else _("smallest first")
	else:
		way = _("Z to A") if descending else _("A to Z")
	summary = [
		{"label": _("Report"), "value": name},
		{"label": _("Of"), "value": _(doctype)},
		{"label": _("Columns"), "value": ", ".join(label(one) for one in shown)},
		{"label": _("Filters"), "value": _said_filters(meta, kept)},
		{"label": _("Sorted by"), "value": f"{label(order)} ({way})"},
	]
	if place:
		summary.append(
			{
				"label": _("Shown in"),
				"value": f"{place['label']} ({_('everybody') if place['everybody'] else _('just you')})",
			}
		)
	route = ["List", doctype, "Report", name]
	return _card(
		"report",
		doctype,
		{"name": name, "settings": settings, "place": place},
		_("Saved report {0}").format(name),
		summary,
		route,
		why,
	)


def suggest_dashboard(
	name: Annotated[str, "What it is called, such as Sales."],
	charts: Annotated[
		list[dict],
		"Each {title, doctype, measure: count|sum|average, field (to add up), over_time (a date field) or group_by "
		"(a field), interval: Daily|Weekly|Monthly|Quarterly|Yearly, timespan: Last Week|Last Month|Last Quarter|"
		"Last Year, filters}.",
	],
	cards: Annotated[list[dict], "Each {label, doctype, measure: count|sum|average, field, filters}."]
	| None = None,
	show_in: Annotated[str, "Also listed in this app's sidebar, such as OneCRM."] | None = None,
	everybody: Annotated[bool, "Listed there for everybody rather than the reader."] = False,
	why: Annotated[str, "In a sentence, what it is for."] | None = None,
) -> dict:
	"""Suggest a dashboard of charts and number cards, made when a workspace
	administrator approves it, under One > Dashboards. A chart counts, adds up
	or averages records over time or by a field. Read describe_type for each
	kind first. Workspace administrators only."""
	if not roles.administers():
		return _mend("suggest_dashboard", "Only a workspace administrator makes dashboards.")
	made_charts, made_cards, summary = [], [], []
	try:
		name = (name or "").strip()
		if not name or frappe.db.exists("Dashboard", name):
			raise Mend("Give the dashboard a name no other dashboard has.")
		for one in (charts or [])[:8]:
			meta = _kind(one.get("doctype"))
			title = str(one.get("title") or "").strip()
			if not title or frappe.db.exists("Dashboard Chart", title):
				raise Mend(
					f"Give each chart a title no other chart has{'; ' + title + ' is taken' if title else ''}."
				)
			measure = str(one.get("measure") or "count").lower()
			if measure not in ("count", "sum", "average"):
				raise Mend("A chart's measure is count, sum or average.")
			field = _field(meta, one["field"], numbers=True) if measure != "count" else None
			if measure != "count" and not field:
				raise Mend(f"{title}: say which number field to {measure}.")
			chart = {
				"doctype": "Dashboard Chart",
				"chart_name": title,
				"document_type": meta.name,
				"filters_json": json.dumps(_filters(meta, one.get("filters"))),
				"is_public": 1,
			}
			if one.get("group_by"):
				chart.update(
					{
						"chart_type": "Group By",
						"group_by_based_on": _field(meta, one["group_by"]),
						"group_by_type": {"count": "Count", "sum": "Sum", "average": "Average"}[measure],
						"aggregate_function_based_on": field,
						"type": "Donut" if measure == "count" else "Bar",
					}
				)
				by = meta.get_field(chart["group_by_based_on"])
				how = _("by {0}").format(_(by.label) if by else chart["group_by_based_on"])
			else:
				when = _field(meta, one.get("over_time") or "creation", dates=True)
				interval = one.get("interval") or "Monthly"
				timespan = one.get("timespan") or "Last Year"
				if interval not in INTERVALS or timespan not in TIMESPANS:
					raise Mend(
						f"{title}: interval is one of {', '.join(INTERVALS)}; timespan one of {', '.join(TIMESPANS)}."
					)
				chart.update(
					{
						"chart_type": {"count": "Count", "sum": "Sum", "average": "Average"}[measure],
						"based_on": when,
						"value_based_on": field,
						"timeseries": 1,
						"time_interval": interval,
						"timespan": timespan,
						"type": "Line" if one.get("type") == "Line" else "Bar",
					}
				)
				how = _("{0}, {1}").format(_(interval), _(timespan))
			made_charts.append(chart)
			summary.append({"label": title, "value": f"{_measured(meta, measure, field)}, {how}"})
		for one in (cards or [])[:8]:
			meta = _kind(one.get("doctype"))
			label = str(one.get("label") or "").strip()
			if not label or frappe.db.exists("Number Card", label):
				raise Mend("Give each card a label no other card has.")
			measure = str(one.get("measure") or "count").lower()
			if measure not in ("count", "sum", "average"):
				raise Mend("A card's measure is count, sum or average.")
			field = _field(meta, one["field"], numbers=True) if measure != "count" else None
			made_cards.append(
				{
					"doctype": "Number Card",
					"label": label,
					"type": "Document Type",
					"document_type": meta.name,
					"function": {"count": "Count", "sum": "Sum", "average": "Average"}[measure],
					"aggregate_function_based_on": field,
					"filters_json": json.dumps(_filters(meta, one.get("filters"))),
					"is_public": 1,
				}
			)
			summary.append({"label": label, "value": _measured(meta, measure, field)})
		if not made_charts and not made_cards:
			raise Mend("A dashboard needs at least one chart or card.")
		place = _place(show_in, everybody)
	except Mend as e:
		return _mend("suggest_dashboard", str(e))
	if place:
		summary.append(
			{
				"label": _("Shown in"),
				"value": f"{place['label']} ({_('everybody') if place['everybody'] else _('just you')})",
			}
		)
	payload = {"name": name, "charts": made_charts, "cards": made_cards, "place": place}
	return _card(
		"dashboard",
		"Dashboard",
		payload,
		_("Dashboard {0}").format(name),
		summary,
		["dashboard-view", name],
		why,
	)


def suggest_report_mail(
	report: Annotated[str, "The report, by name: a saved one or an app's, such as Accounts Receivable."],
	to: Annotated[list[str], "Addresses to send it to."],
	frequency: Annotated[str, "Daily, Weekdays, Weekly or Monthly."] = "Weekly",
	day: Annotated[str, "For weekly, the day, such as Monday."] | None = "Monday",
	format: Annotated[str, "HTML in the mail, or XLSX or CSV attached."] = "HTML",
	why: Annotated[str, "In a sentence, what it is for."] | None = None,
) -> dict:
	"""Suggest a report sent by mail on a schedule, run as whoever approves it
	would see it. Workspace administrators only."""
	if not roles.administers():
		return _mend("suggest_report_mail", "Only a workspace administrator sends reports by mail.")
	if not frappe.db.exists("Report", report) or not frappe.get_doc("Report", report).is_permitted():
		return _mend(
			"suggest_report_mail",
			f"{report} is not a report the reader may open; workspace_reports names the saved ones.",
		)
	if frequency not in FREQUENCIES or format not in FORMATS or (frequency == "Weekly" and day not in DAYS):
		return _mend(
			"suggest_report_mail",
			f"frequency is one of {', '.join(FREQUENCIES)}; format one of {', '.join(FORMATS)}; a weekly one needs a day.",
		)
	addresses = [str(one).strip() for one in to or [] if str(one).strip()]
	if not addresses or any(not validate_email_address(one) for one in addresses):
		return _mend("suggest_report_mail", "Give the addresses it goes to.")
	doc = {
		"doctype": "Auto Email Report",
		"report": report,
		"enabled": 1,
		"email_to": "\n".join(addresses),
		"frequency": frequency,
		"day_of_week": day if frequency == "Weekly" else None,
		"format": format,
		"send_if_data": 1,
	}
	summary = [
		{"label": _("Report"), "value": report},
		{"label": _("To"), "value": ", ".join(addresses)},
		{"label": _("How often"), "value": _(frequency) + (f", {_(day)}" if frequency == "Weekly" else "")},
		{"label": _("As"), "value": format},
	]
	return _card(
		"mail",
		"Auto Email Report",
		{"doc": doc},
		_("Mail {0}").format(report),
		summary,
		["List", "Auto Email Report"],
		why,
	)


def _rights(said: list | None) -> list:
	"""[{doctype, rights}] with each right in frappe's word."""
	rows = []
	for one in said or []:
		rights = set()
		for word in one.get("rights") or []:
			right = RIGHT_WORDS.get(str(word).strip().lower())
			if not right:
				raise Mend(f"{word} is not a right; one of {', '.join(sorted(set(RIGHT_WORDS)))}.")
			rights.add(right)
		if one.get("doctype") and rights:
			rows.append({"doctype": one["doctype"], "rights": sorted(rights, key=access.RIGHTS.index)})
	return rows


def _changed(rows: list, give: list, take: list) -> list:
	"""A level's rows with rights given and taken away."""
	have = {row["doctype"]: {r for r in access.RIGHTS if row.get(r)} for row in rows}
	for one in give:
		have.setdefault(one["doctype"], set()).update(one["rights"])
	for one in take:
		have.setdefault(one["doctype"], set()).difference_update(one["rights"])
	return [
		{"doctype": d, **{r: int(r in rights) for r in access.RIGHTS}} for d, rights in have.items() if rights
	]


def _state(rows: list) -> str:
	return hashlib.sha1(
		json.dumps(sorted(rows, key=lambda r: r["doctype"]), sort_keys=True).encode()
	).hexdigest()[:12]


def suggest_level(
	app: Annotated[str, "OneCRM, OneBook, OneInventory, OneProject or OneHR."],
	name: Annotated[
		str, "The level: User, Manager, one of the workspace's own, or a new one such as Senior Sales."
	],
	give: Annotated[
		list[dict],
		"Rights to give, each {doctype, rights: [read, edit, create, delete, submit, cancel, export, pick]}.",
	]
	| None = None,
	take: Annotated[list[dict], "Rights to take away, the same way."] | None = None,
	starts_as: Annotated[str, "For a new level, the level it starts as: User, Manager or another."] = "User",
	why: Annotated[str, "In a sentence, what the level is for."] | None = None,
) -> dict:
	"""Suggest a level of an app made, or what a level may do changed: rights
	on kinds of record given or taken away. Read workspace_access first. The
	card names every right in plain words; what a right needs, and the kinds a
	record must name, come with it when it is approved. Workspace
	administrators only."""
	if not roles.administers():
		return _mend("suggest_level", "Only a workspace administrator changes levels.")
	from onedesk.one.settings import APPS

	try:
		if app not in {one[0] for one in APPS}:
			raise Mend(f"{app} is not an app; one of {', '.join(one[0] for one in APPS)}.")
		name = (name or "").strip()
		known = access.tiers(app)
		new = name not in known
		if new:
			if not name or ":" in name or frappe.db.exists("Role", name):
				raise Mend(f"{name} is taken or not a name a level can have.")
			if starts_as not in known:
				raise Mend(f"A new level starts as one of {', '.join(known)}.")
		give, take = _rights(give), _rights(take)
		allowed = set(access.kinds(app))
		for one in give:
			if one["doctype"] not in allowed:
				raise Mend(f"{one['doctype']} is not a kind of record {app} works with.")
		key = access.key_of(app, starts_as if new else name)
		rows = access.level(key)["rows"]
		# Only what would change: a right it holds already is not given, nor
		# one it lacks taken away, so the card says no more than happens.
		have = {row["doctype"]: {r for r in access.RIGHTS if row.get(r)} for row in rows}
		give = [
			g
			for g in (
				{**one, "rights": [r for r in one["rights"] if r not in have.get(one["doctype"], ())]}
				for one in give
			)
			if g["rights"]
		]
		take = [
			t
			for t in (
				{**one, "rights": [r for r in one["rights"] if r in have.get(one["doctype"], ())]}
				for one in take
			)
			if t["rights"]
		]
		if not give and not take and not new:
			raise Mend(
				f"{name} already has every right asked to give and none asked to take away; nothing would change."
			)
	except Mend as e:
		return _mend("suggest_level", str(e))
	called = name if name not in access.BASE else _("{0} {1}").format(app, _(name))
	summary = (
		[]
		if not new
		else [{"label": _("New level"), "value": _("{0}, starting as {1}").format(name, _(starts_as))}]
	)
	for one in give:
		kind = one["doctype"]
		said = ", ".join(_(VERB[r]) for r in one["rights"])
		summary.append({"label": _(kind), "value": _("may now {0}").format(said)})
	for one in take:
		kind = one["doctype"]
		said = ", ".join(_(VERB[r]) for r in one["rights"])
		summary.append({"label": _(kind), "value": _("may no longer {0}").format(said)})
	people = len(access.people_at(app, name)) if not new else 0
	if people:
		summary.append(
			{
				"label": _("Who it changes"),
				"value": _("{0} people at this level, who are told").format(people),
			}
		)
	payload = {
		"app": app,
		"name": name,
		"new": int(new),
		"starts_as": starts_as,
		"give": give,
		"take": take,
		"state": _state(rows),
	}
	route = [
		"workspace-settings",
		{"section": "access", "level": access.key_of(app, name) if not new else name},
	]
	return _card(
		"level",
		"Role",
		payload,
		_("Level {0}").format(called) if not new else _("New level {0}").format(name),
		summary,
		route,
		why,
	)


def suggest_profile(
	name: Annotated[str, "The profile, such as Accountant: one that exists, or a new one."],
	levels: Annotated[
		dict,
		'Each app\'s level, such as {"OneBook": "Manager", "OneInventory": "User"}; an app left out is None.',
	],
	why: Annotated[str, "In a sentence, what job it is for."] | None = None,
) -> dict:
	"""Suggest a profile made or changed: a job's level in each app, set on a
	person's page at once. Workspace administrators only."""
	if not roles.administers():
		return _mend("suggest_profile", "Only a workspace administrator makes profiles.")
	from onedesk.one.settings import APPS, LEVELS

	name = (name or "").strip()
	if not name:
		return _mend("suggest_profile", "Give the profile a name.")
	own = access.all_levels()
	said = {}
	for app, _icon, _used, _managed in APPS:
		level = (levels or {}).get(app) or "None"
		if level not in LEVELS and level not in own.get(app, ()):
			return _mend(
				"suggest_profile",
				f"{level} is not a level of {app}; one of {', '.join([*LEVELS, *own.get(app, [])])}.",
			)
		said[app] = level
	exists = bool(frappe.db.exists("Role Profile", name))
	summary = [{"label": app, "value": _(level)} for app, level in said.items() if level != "None"] or [
		{"label": _("Apps"), "value": _("None beyond the five everybody has")}
	]
	if exists:
		summary.append({"label": _("Who it changes"), "value": _("Everybody on {0}").format(name)})
	route = ["workspace-settings", {"section": "access", "profile": name}]
	return _card(
		"profile",
		"Role Profile",
		{"name": name, "exists": int(exists), "levels": said},
		_("Profile {0}").format(name),
		summary,
		route,
		why,
	)


def suggest_group(
	name: Annotated[str, "The group, such as Sales Gulf: one that exists, or a new one."],
	members: Annotated[list[str], "Everybody in it once approved, by address or name."],
	why: Annotated[str, "In a sentence, what the group is for."] | None = None,
) -> dict:
	"""Suggest a group made or its people changed: a team by name, assigned to
	or mentioned at once. Workspace administrators only."""
	if not roles.administers():
		return _mend("suggest_group", "Only a workspace administrator makes groups.")
	name = (name or "").strip()
	try:
		if not name:
			raise Mend("Give the group a name.")
		people = list(dict.fromkeys(_person(one) for one in members or []))
		if not people:
			raise Mend("A group needs somebody in it.")
	except Mend as e:
		return _mend("suggest_group", str(e))
	exists = bool(frappe.db.exists("User Group", name))
	was = (
		set(
			frappe.get_all(
				"User Group Member", filters={"parent": name, "parenttype": "User Group"}, pluck="user"
			)
		)
		if exists
		else set()
	)
	label = lambda users: ", ".join(frappe.utils.get_fullname(u) for u in users)  # noqa: E731
	summary = [{"label": _("In it"), "value": label(people)}]
	if exists and set(people) - was:
		summary.append({"label": _("Joining"), "value": label(sorted(set(people) - was))})
	if exists and was - set(people):
		summary.append({"label": _("Leaving"), "value": label(sorted(was - set(people)))})
	route = ["workspace-settings", {"section": "access", "group": name}]
	return _card(
		"group",
		"User Group",
		{"name": name, "exists": int(exists), "members": people},
		_("Group {0}").format(name),
		summary,
		route,
		why,
	)


def suggest_hold(
	person: Annotated[str, "Who, by address or name."],
	kind: Annotated[
		str, "Territory, Customer Group, Customer, Supplier, Department, Branch, Project or Warehouse."
	],
	record: Annotated[str, "Which one, such as United Arab Emirates."],
	only_on: Annotated[str, "Only on this kind of record, such as Sales Invoice; left out, everywhere."]
	| None = None,
	let_go: Annotated[
		bool, "Take this hold away instead, so they see everything their apps show again."
	] = False,
	why: Annotated[str, "In a sentence, why."] | None = None,
) -> dict:
	"""Suggest what a person sees: held to one territory, department, customer
	group or other record so they see only its records, or let go of one.
	Read workspace_access first. Workspace administrators only."""
	if not roles.administers():
		return _mend("suggest_hold", "Only a workspace administrator changes what a person sees.")
	try:
		user = _person(person)
		if kind not in access.RECORD_KINDS:
			raise Mend(f"A person is held to one of {', '.join(access.RECORD_KINDS)}.")
		if not frappe.db.exists(kind, record):
			raise Mend(f"There is no {kind} {record}.")
		if only_on and not frappe.db.exists("DocType", only_on):
			raise Mend(f"{only_on} is not a kind of record.")
		held = frappe.db.get_value(
			"User Permission",
			{"user": user, "allow": kind, "for_value": record, "applicable_for": only_on or None},
		)
		if let_go and not held:
			raise Mend(f"{person} is not held to {kind} {record}.")
		if held and not let_go:
			raise Mend(f"{person} is held to {kind} {record} already.")
	except Mend as e:
		return _mend("suggest_hold", str(e))
	who = frappe.utils.get_fullname(user)
	where = _("only on {0}").format(_(only_on)) if only_on else _("everywhere")
	value = (
		_("no longer only the records of {0} {1}").format(_(kind), record)
		if let_go
		else _("only the records of {0} {1}, {2}").format(_(kind), record, where)
	)
	summary = [{"label": who, "value": value}, {"label": _("Told"), "value": _("Yes, on their bell")}]
	payload = {
		"user": user,
		"kind": kind,
		"record": record,
		"only_on": only_on,
		"let_go": int(bool(let_go)),
		"hold": held,
	}
	route = ["workspace-settings", {"section": "people", "person": user}]
	return _card("hold", "User Permission", payload, _("What {0} sees").format(who), summary, route, why)


for _tool in (
	suggest_saved_report,
	suggest_dashboard,
	suggest_report_mail,
	suggest_level,
	suggest_profile,
	suggest_group,
	suggest_hold,
):
	_tool.action = "workspace_setup"


# ------------------------------------------------------------------ approving


def apply(changes: dict) -> str:
	"""A Setup card approved: the page's own code, as whoever pressed Approve.
	Returns what was made or changed."""
	what = changes.get("what")
	if what == "report":
		from frappe.desk.reportview import save_report

		name = save_report(
			changes["name"], changes["settings"]["fields"][0][1], json.dumps(changes["settings"])
		)
		place = changes.get("place")
		if place:
			reports.place("Report", name, place["module"], place["everybody"])
		return name
	if what == "dashboard":
		roles.require()
		for one in changes.get("charts") or []:
			frappe.get_doc(one).insert()
		for one in changes.get("cards") or []:
			frappe.get_doc(one).insert()
		made = frappe.get_doc(
			{
				"doctype": "Dashboard",
				"dashboard_name": changes["name"],
				"charts": [
					{"chart": one["chart_name"], "width": "Full"} for one in changes.get("charts") or []
				],
				"cards": [{"card": one["label"]} for one in changes.get("cards") or []],
			}
		).insert()
		place = changes.get("place")
		if place:
			reports.place("Dashboard", made.name, place["module"], place["everybody"])
		return made.name
	if what == "mail":
		roles.require()
		# It runs as, and shows what is seen by, whoever approved it.
		return frappe.get_doc({**changes["doc"], "user": frappe.session.user}).insert().name
	if what == "level":
		roles.require()
		app, name = changes["app"], changes["name"]
		key = access.key_of(app, changes["starts_as"] if changes.get("new") else name)
		if _state(access.level(key)["rows"]) != changes["state"]:
			raise frappe.ValidationError(
				_("{0} has changed since this was suggested, so it no longer applies.").format(name)
			)
		if changes.get("new"):
			key = access.new_level(app, name, changes["starts_as"])
		rows = _changed(access.level(key)["rows"], changes.get("give") or [], changes.get("take") or [])
		return access.save_level(key, name if name not in access.BASE else None, rows)
	if what == "profile":
		return access.save_profile(
			changes["name"] if changes.get("exists") else None, changes["name"], changes["levels"]
		)
	if what == "group":
		return access.save_group(
			changes["name"] if changes.get("exists") else None, changes["name"], changes["members"]
		)
	if what == "extension":
		from onedesk.one_studio import ai

		return ai.turn_on(changes)
	if what == "hold":
		if changes.get("let_go"):
			access.let_go(changes["hold"])
		else:
			access.hold(changes["user"], changes["kind"], changes["record"], changes.get("only_on"))
		return changes["user"]
	frappe.throw(_("That cannot be set."))
