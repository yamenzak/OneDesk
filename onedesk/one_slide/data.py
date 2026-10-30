"""Words on a slide that come from records (AGENTS.md, Data from records).

A presentation names its sources, and a text holds chips (`{key.field}`)
filled each time the slide is drawn, as whoever is looking: what they may
not read is empty. Freeze Data writes the values in for good, and One for
Each makes a copy of the presentation on each record of a list.
"""

import json
import re
from typing import Annotated

import frappe
from frappe import _

KINDS = ("this", "record", "linked", "list")
KEY = re.compile(r"^[a-z][a-z0-9_]{0,29}$")
CHIP = re.compile(r"\{([a-z][a-z0-9_]{0,29})\.([a-z0-9_.]{1,80})\}")
MOST_SOURCES = 12
MOST_ROWS = 50
OPERATORS = ("=", "!=", ">", "<", ">=", "<=", "like")


def cleaned(sources) -> list[dict]:
	"""Sources as kept: known kinds, keys once each, a list's rows capped. Pure."""
	if isinstance(sources, str):
		try:
			sources = json.loads(sources or "[]")
		except ValueError:
			return []
	kept, keys = [], set()
	for one in sources if isinstance(sources, list) else []:
		if not isinstance(one, dict) or one.get("kind") not in KINDS or not KEY.match(str(one.get("key") or "")):
			continue
		if one["key"] in keys:
			continue
		keys.add(one["key"])
		out = {"key": one["key"], "kind": one["kind"]}
		for field in ("doctype", "name", "from", "field", "order_by", "sample"):
			if one.get(field):
				out[field] = str(one[field])[:140]
		if one["kind"] == "list":
			out["limit"] = max(1, min(int(one.get("limit") or 10), MOST_ROWS))
			out["filters"] = [
				[str(f[0])[:80], f[1] if f[1] in OPERATORS else "=", str(f[2])[:140]]
				for f in one.get("filters") or []
				if isinstance(f, list | tuple) and len(f) == 3
			]
		kept.append(out)
	return kept[:MOST_SOURCES]


def chips(texts) -> set[tuple[str, str]]:
	"""Every chip the texts hold, as (source, the rest). Pure."""
	return {(m[1], m[2]) for text in texts if isinstance(text, str) for m in CHIP.finditer(text)}


def fill(html: str, values: dict) -> str:
	"""A text with each chip it holds a value for put in. Pure."""
	from frappe.utils import escape_html

	return CHIP.sub(lambda m: escape_html(values[m[0][1:-1]]) if m[0][1:-1] in values else m[0], html or "")


ROW = re.compile(r"<tr\b[^>]*>.*?</tr>", re.S)


def tabled(html: str, values: dict) -> str:
	"""A table filled, without the rows of a list that ran out. Pure."""
	from frappe.utils import strip_html

	def row(match):
		done = fill(match[0], values)
		if not CHIP.search(match[0]):
			return done
		done = CHIP.sub("", done)
		return done if strip_html(done).replace("\u200b", "").strip() else ""

	return ROW.sub(row, html or "")


def _texts(name: str) -> list[str]:
	from onedesk.one_slide import master

	out = []
	rows = frappe.get_all("Presentation Slide", filters={"parent": name, "parenttype": "Presentation"}, pluck="elements")
	for kept in rows + [json.dumps(master.elements(name))]:
		for one in json.loads(kept or "[]"):
			if isinstance(one, dict) and isinstance(one.get("content"), str):
				out.append(one["content"])
	return out


def _shown(doc, field: str) -> str:
	"""One field of a record as a print shows it, or nothing when the reader may not see it."""
	from frappe.utils import strip_html

	meta = frappe.get_meta(doc.doctype)
	df = meta.get_field(field)
	if field == "name":
		return str(doc.name)
	if not df or df.fieldtype in frappe.model.no_value_fields or df.fieldtype in ("Password", "Attach Image", "Table", "Table MultiSelect"):
		return ""
	if df.permlevel and not doc.has_permlevel_access_to(field):
		return ""
	return strip_html(frappe.format(doc.get(field), df, doc) or "").strip()


def _readable(doctype: str, name: str):
	if not doctype or not name or not frappe.db.exists(doctype, name):
		return None
	if not frappe.has_permission(doctype, "read", doc=name):
		return None
	return frappe.get_doc(doctype, name)


def _resolve(name: str, sources: list[dict]) -> tuple[dict, dict]:
	"""Each source as the reader may see it: a record, or a list's rows."""
	from onedesk.one_slide import api

	item = api._file(name)
	records, lists = {}, {}
	for one in sources:
		kind = one["kind"]
		if kind == "this":
			if item.get("attached_to_doctype") and item.get("attached_to_name"):
				records[one["key"]] = _readable(item["attached_to_doctype"], item["attached_to_name"])
			else:
				records[one["key"]] = _readable(one.get("doctype"), one.get("sample"))
		elif kind == "record":
			records[one["key"]] = _readable(one.get("doctype"), one.get("name"))
		elif kind == "linked":
			parent = records.get(one.get("from"))
			df = frappe.get_meta(parent.doctype).get_field(one.get("field")) if parent else None
			target = df.options if df and df.fieldtype == "Link" else None
			records[one["key"]] = _readable(target, parent.get(one["field"])) if target else None
		elif kind == "list" and one.get("doctype") and frappe.db.exists("DocType", one["doctype"]):
			filters = []
			for field, operator, value in one.get("filters") or []:
				said = CHIP.fullmatch(value)
				if said:
					source = records.get(said[1])
					value = (source.name if said[2] == "name" else source.get(said[2])) if source else None
					if value is None:
						filters = None
						break
				filters.append([field, operator, value])
			if filters is None:
				lists[one["key"]] = []
				continue
			try:
				names = frappe.get_list(one["doctype"], filters=filters, pluck="name", order_by=one.get("order_by") or "modified desc", limit=one.get("limit") or 10)
			except (frappe.PermissionError, frappe.ValidationError):
				names = []
			lists[one["key"]] = [frappe.get_doc(one["doctype"], row) for row in names]
	return records, lists


def evaluate(name: str, wanted: set | None = None) -> dict:
	"""Every chip the presentation holds (or the editor asks for, not yet
	saved), filled as the reader may see it, and the records it read, for the
	editor to listen to."""
	from frappe.utils import flt, fmt_money

	sources = cleaned(frappe.db.get_value("Presentation", name, "sources"))
	if not sources:
		return {"values": {}, "watch": []}
	records, lists = _resolve(name, sources)
	values, watch = {}, []
	for key, rest in chips(_texts(name)) | (wanted or set()):
		chip = f"{key}.{rest}"
		parts = rest.split(".")
		if key in records:
			doc = records[key]
			values[chip] = _shown(doc, rest) if doc and len(parts) == 1 else ""
			if doc:
				watch.append([doc.doctype, doc.name])
		elif key in lists:
			rows = lists[key]
			if parts == ["count"]:
				values[chip] = str(len(rows))
			elif parts[0] == "sum" and len(parts) == 2:
				values[chip] = fmt_money(sum(flt(row.get(parts[1])) for row in rows)) if rows else "0"
			elif len(parts) == 2 and parts[0].isdigit():
				at = int(parts[0]) - 1
				values[chip] = _shown(rows[at], parts[1]) if 0 <= at < len(rows) else ""
	return {"values": values, "watch": [list(one) for one in {tuple(one) for one in watch}]}


def poured(name: str, rows: list[dict], reader: str | None = None) -> list[dict]:
	"""Rows as kept, every chip filled, for what draws slides without the editor
	(the TV, PowerPoint). A screen has no reader, so it reads as `reader`."""
	if not cleaned(frappe.db.get_value("Presentation", name, "sources")):
		return rows
	was = frappe.session.user
	if reader and reader != was:
		frappe.set_user(reader)
	try:
		said = evaluate(name)["values"]
	finally:
		if frappe.session.user != was:
			frappe.set_user(was)
	out = []
	for row in rows:
		drawn = json.loads(row.get("elements") or "[]") if isinstance(row.get("elements"), str) else row.get("elements") or []
		for one in drawn:
			if isinstance(one, dict) and isinstance(one.get("content"), str):
				one["content"] = (tabled if one.get("type") == "table" else fill)(one["content"], said)
		out.append({**row, "elements": json.dumps(drawn)})
	return out


@frappe.whitelist()
@frappe.read_only()
def values(
	name: Annotated[str, "The presentation."],
	asked: Annotated[str | list | None, "Chips on the slides not saved yet, as {key.field}."] = None,
) -> dict:
	"""What the presentation's chips say, as the reader may see it."""
	from onedesk.one_slide import api

	api._may(name, "read")
	asked = frappe.parse_json(asked) if isinstance(asked, str) else asked
	return evaluate(name, chips([" ".join(str(one) for one in (asked or [])[:400])]))


@frappe.whitelist(methods=["POST"])
def save_sources(name: Annotated[str, "The presentation."], sources: Annotated[str | list, "Its sources."]) -> list[dict]:
	"""The presentation's sources, each a doctype the person may read."""
	from onedesk.one_slide import api

	api._may(name, "write")
	kept = cleaned(sources)
	for doctype in {one.get("doctype") for one in kept} - {None}:
		if not frappe.has_permission(doctype, "read"):
			frappe.throw(_("You may not read {0}, so it can't be a source.").format(_(doctype)), frappe.PermissionError)
	frappe.db.set_value("Presentation", name, "sources", json.dumps(kept), update_modified=False)
	return kept


@frappe.whitelist()
@frappe.read_only()
def fields(doctype: Annotated[str, "A record type."]) -> list[dict]:
	"""The fields of a record type a chip can show, and its link fields."""
	if not frappe.has_permission(doctype, "read"):
		return []
	meta = frappe.get_meta(doctype)
	out = [{"fieldname": "name", "label": _("ID"), "fieldtype": "Data"}]
	for df in meta.fields:
		if df.fieldtype in frappe.model.no_value_fields or df.fieldtype in ("Password", "Table", "Table MultiSelect") or df.hidden or df.fieldname == "naming_series":
			continue
		out.append({"fieldname": df.fieldname, "label": _(df.label or df.fieldname), "fieldtype": df.fieldtype, "options": df.options if df.fieldtype == "Link" else None, "in_list_view": df.in_list_view})
	return out


@frappe.whitelist(methods=["POST"])
def freeze(name: Annotated[str, "The presentation."]) -> dict:
	"""Every chip written in as it reads now, for good; what it was is a version."""
	from onedesk.one_slide import api, versions

	api._may(name, "write")
	said = evaluate(name)["values"]
	doc = frappe.get_doc("Presentation", name)
	versions.keep_now(doc, _("Before freezing the data"))
	for row in doc.slides:
		drawn = json.loads(row.elements or "[]")
		for one in drawn:
			if isinstance(one, dict) and isinstance(one.get("content"), str):
				one["content"] = fill(one["content"], said)
		row.elements = json.dumps(drawn)
	doc.save(ignore_permissions=True)
	return {"frozen": len(said)}


@frappe.whitelist(methods=["POST"])
def for_each(
	name: Annotated[str, "The presentation, whose first source is the record it is for."],
	names: Annotated[str | list, "The records to make one for."],
) -> dict:
	"""A copy of the presentation filed on each record, made in the background."""
	from onedesk.one_slide import api

	item = api._may(name, "read")
	this = next((one for one in cleaned(frappe.db.get_value("Presentation", name, "sources")) if one["kind"] == "this"), None)
	if not this or not this.get("doctype"):
		frappe.throw(_("Add a source for the record this is for first."))
	names = frappe.parse_json(names) if isinstance(names, str) else names
	names = [str(one) for one in names or [] if frappe.has_permission(this["doctype"], "write", doc=str(one))][:200]
	if not names:
		frappe.throw(_("Could not make presentations: there are no records you may file one on."))
	frappe.enqueue(made_for_each, queue="long", name=name, title=item["file_name"], doctype=this["doctype"], names=names, user=frappe.session.user, enqueue_after_commit=True)
	return {"queued": len(names)}


def made_for_each(name: str, title: str, doctype: str, names: list, user: str) -> None:
	"""The background job: one copy per record, then a word to whoever asked."""
	from onedesk.one_slide import api

	frappe.set_user(user)
	made = 0
	for record in names:
		file = frappe.get_doc(
			{
				"doctype": "File",
				"file_url": api.URL + name,
				"is_private": 1,
				"attached_to_doctype": doctype,
				"attached_to_name": record,
				"file_name": f"{title} - {record}",
			}
		)
		file.flags.ignore_permissions = True
		file.insert()
		made += 1
	frappe.publish_realtime("one_slide_for_each", {"made": made, "doctype": doctype}, user=user, after_commit=True)
