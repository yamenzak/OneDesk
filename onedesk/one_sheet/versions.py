"""A workbook's history: every edit in the order it was saved (Workbook
Change), and the workbook whole at points along the way (Workbook Version).
After Frappe Suite's sheets/versioning: the log is the record, a version is a
checkpoint, and the workbook row is the head. AGENTS.md, versions.py.
"""

import json
import re
from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import cint, get_datetime, now_datetime

from onedesk.one_sheet import api, storage

CHANGE, VERSION = "Workbook Change", "Workbook Version"

#: Edits one save may carry.
MOST_OPS = 500

#: A version is taken on the first save, then every so many edits or seconds.
EVERY_OPS, EVERY_SECONDS = 25, 30

#: Unnamed versions are thinned as they age: all for a day, then one an hour
#: to a week, one a day to a month, one a week to three months, then none.
THINNED = ((timedelta(days=1), None), (timedelta(days=7), "%Y-%m-%d %H"), (timedelta(days=30), "%Y-%m-%d"), (timedelta(days=90), "%Y-%W"))

#: Edits older than this go, once a version holds what they made.
KEPT_DAYS = 30

CELL = re.compile(r"^[A-Z]{1,3}[0-9]{1,7}$")


def record(workbook: str, ops: str | list | None, byte_size: int, request_id: str | None = None) -> int:
	"""Append a save's edits and the save itself under one lock, and answer the
	new head. A request sent twice is recorded once."""
	if request_id and frappe.db.exists(CHANGE, {"workbook": workbook, "request_id": request_id}):
		return cint(frappe.db.get_value(api.WORKBOOK, workbook, "head_seq"))
	ops = _ops(ops)
	head = cint(frappe.db.sql("select head_seq from `tabWorkbook` where name = %s for update", workbook)[0][0])
	actor = frappe.session.user
	for at, op in enumerate(ops, 1):
		_insert(workbook, head + at, op, actor)
	head += len(ops) + 1
	_insert(workbook, head, {"op_type": "save", "summary": _sized(byte_size)}, actor, request_id)
	frappe.db.set_value(api.WORKBOOK, workbook, "head_seq", head, update_modified=False)
	return head


def _ops(ops) -> list[dict]:
	if not ops:
		return []
	if isinstance(ops, str):
		try:
			ops = json.loads(ops)
		except ValueError:
			frappe.throw(_("The edits in this save are invalid."))
	if not isinstance(ops, list):
		frappe.throw(_("The edits in this save are invalid."))
	if len(ops) > MOST_OPS:
		frappe.throw(_("Too many edits in one save."))
	return ops


def _insert(workbook: str, seq: int, op: dict, actor: str, request_id: str | None = None) -> None:
	kind = op.get("op_type") or op.get("opType")
	if not kind:
		frappe.throw(_("Each edit must specify its type."))
	refs = op.get("cell_refs") or op.get("cellRefs")
	before = op.get("before") or op.get("before_json")
	after = op.get("after") or op.get("after_json")
	frappe.get_doc(
		{
			"doctype": CHANGE,
			"workbook": workbook,
			"seq": seq,
			"op_type": str(kind)[:140],
			"sub_sheet": op.get("sub_sheet") or op.get("subSheet"),
			"cell_refs": refs if isinstance(refs, str) or refs is None else json.dumps(refs),
			"before_json": before if isinstance(before, str) or before is None else json.dumps(before),
			"after_json": after if isinstance(after, str) or after is None else json.dumps(after),
			"summary": (op.get("summary") or "")[:140],
			"actor": actor,
			"request_id": request_id,
		}
	).db_insert()


def _sized(size: int) -> str:
	for unit, scale in (("MB", 1 << 20), ("KB", 1 << 10)):
		if size >= scale:
			return f"Saved ({size / scale:.1f} {unit})"
	return f"Saved ({size} B)"


def maybe_take(workbook: str) -> str | None:
	"""A version at the head, when enough has happened since the last one."""
	head = cint(frappe.db.get_value(api.WORKBOOK, workbook, "head_seq"))
	last = _last(workbook)
	if head <= 0 or (last and head <= last.seq):
		return None
	if last and head - last.seq < EVERY_OPS and (now_datetime() - get_datetime(last.creation)).total_seconds() < EVERY_SECONDS:
		return None
	return take(workbook)


def take(workbook: str, kind: str = "auto", label: str | None = None) -> str:
	held = frappe.db.get_value(api.WORKBOOK, workbook, ["sheets_data", "head_seq"], as_dict=True)
	last = _last(workbook)
	doc = frappe.get_doc(
		{
			"doctype": VERSION,
			"workbook": workbook,
			"seq": cint(held.head_seq),
			"kind": kind,
			"label": (label or "").strip()[:140] or None,
			"pinned": int(kind == "named"),
			"op_count": max(0, cint(held.head_seq) - (last.seq if last else 0)),
			"byte_size": len(held.sheets_data or ""),
			"actor": frappe.session.user,
			"sheets_data": held.sheets_data,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def _last(workbook: str):
	found = frappe.get_all(VERSION, filters={"workbook": workbook}, fields=["name", "seq", "creation"], order_by="seq desc", limit=1)
	return found[0] if found else None


def _version(name: str, ptype: str = "read") -> dict:
	held = frappe.db.get_value(VERSION, name, ["name", "workbook", "seq", "kind", "label", "pinned", "sheets_data"], as_dict=True)
	if not held:
		frappe.throw(_("This version no longer exists."), frappe.DoesNotExistError)
	api._may(held.workbook, ptype)
	return held


@frappe.whitelist()
@frappe.read_only()
def timeline(sheet: str, tz_offset_minutes: int = 0, bucket_limit: int = 40) -> dict:
	"""The versions the history panel lists: those kept by name, then the newest."""
	api._may(sheet)
	fields = ["name", "seq", "kind", "label", "pinned", "op_count", "actor", "creation"]
	kept = frappe.get_all(VERSION, filters={"workbook": sheet, "pinned": 1}, fields=fields, order_by="seq desc")
	newest = frappe.get_all(VERSION, filters={"workbook": sheet}, fields=fields, order_by="seq desc", limit=cint(bucket_limit) * 4)
	return {"buckets": {"pinned": {"items": [_said(one) for one in kept]}, "earlier": {"items": [_said(one) for one in newest]}}}


def _said(row) -> dict:
	return {
		"id": row.name,
		"seq": cint(row.seq),
		"kind": row.kind,
		"label": row.label,
		"pinned": bool(row.pinned),
		"op_count": cint(row.op_count),
		"actor": row.actor,
		"actor_name": frappe.utils.get_fullname(row.actor) if row.actor else "",
		"creation": row.creation.isoformat() if row.creation else None,
	}


@frappe.whitelist()
@frappe.read_only()
def state_at(snapshot: str) -> dict:
	held = _version(snapshot)
	return {"sheets_data": storage.decode_sheets_data(held.sheets_data), "label": held.label, "seq": held.seq}


@frappe.whitelist(methods=["POST"])
def restore(snapshot: str) -> dict:
	"""Make a version the head again, as an edit on top of the history rather
	than a rewind of it, and keep the moment as a milestone."""
	held = _version(snapshot, "write")
	head = record(held.workbook, [{"op_type": "restore", "summary": f"Restored version {held.seq}"}], len(held.sheets_data or ""))
	frappe.db.set_value(api.WORKBOOK, held.workbook, {"sheets_data": held.sheets_data, "head_seq": head}, update_modified=True)
	return {"name": held.workbook, "head_seq": head, "snapshot": take(held.workbook, "milestone")}


@frappe.whitelist(methods=["POST"])
def label_snapshot(snapshot: str, label: str = "", pinned: int | None = None) -> dict:
	"""Name a version, which keeps it; an empty name lets it age like the rest."""
	held = _version(snapshot, "write")
	label = (label or "").strip()[:140]
	keep = int(bool(label)) if pinned is None else cint(pinned)
	frappe.db.set_value(VERSION, snapshot, {"label": label or None, "pinned": keep, "kind": "named" if keep else (held.kind if held.kind != "named" else "auto")})
	return {"name": snapshot, "label": label, "pinned": bool(keep)}


@frappe.whitelist(methods=["POST"])
def make_copy(snapshot: str, title: str = "") -> str:
	"""A new workbook beside this one, holding the version as it was."""
	held = _version(snapshot)
	item = api._file(held.workbook)
	made = api.make(item.get("folder") or "@my", title or _("{0} (copy)").format(item["file_name"]))
	frappe.db.set_value(api.WORKBOOK, made["workbook"], "sheets_data", held.sheets_data)
	return made["workbook"]


@frappe.whitelist()
@frappe.read_only()
def ops_for_cell(sheet: str, cell_id: str, sub_sheet: str | None = None, limit: int = 50) -> list[dict]:
	"""Every edit that touched one cell, newest first, with the cell before and after."""
	api._may(sheet)
	if not CELL.match(cell_id or ""):
		frappe.throw(_("Invalid cell reference."))
	filters = {"workbook": sheet, "cell_refs": ["like", f'%"{cell_id}"%']}
	if sub_sheet:
		filters["sub_sheet"] = sub_sheet
	rows = frappe.get_all(
		CHANGE,
		filters=filters,
		fields=["name", "seq", "sub_sheet", "op_type", "cell_refs", "before_json", "after_json", "summary", "actor", "creation"],
		order_by="seq desc",
		limit=min(cint(limit) or 50, 200),
	)
	out = []
	for row in rows:
		refs, before, after = (_json(row.cell_refs), _json(row.before_json) or {}, _json(row.after_json) or {})
		if isinstance(refs, list) and cell_id not in refs:
			continue
		out.append(
			{
				"id": row.name,
				"seq": cint(row.seq),
				"sub_sheet": row.sub_sheet,
				"op_type": row.op_type,
				"summary": row.summary,
				"actor": row.actor,
				"actor_name": frappe.utils.get_fullname(row.actor) if row.actor else "",
				"creation": row.creation.isoformat() if row.creation else None,
				"before": before.get(cell_id) if isinstance(before, dict) else None,
				"after": after.get(cell_id) if isinstance(after, dict) else None,
			}
		)
	return out


def _json(value):
	try:
		return json.loads(value) if value else None
	except ValueError:
		return None


def thinned(rows: list[dict], now) -> list[str]:
	"""The unnamed versions to delete as they age (THINNED): the newest of
	each hour, day or week is kept. Pure."""
	gone, seen = [], set()
	for row in sorted(rows, key=lambda one: one["creation"], reverse=True):
		age = now - row["creation"]
		bucket = next(((until, shape) for until, shape in THINNED if age <= until), None)
		if bucket is None:
			gone.append(row["name"])
			continue
		if bucket[1] is None:
			continue
		key = (bucket[1], row["creation"].strftime(bucket[1]))
		if key in seen:
			gone.append(row["name"])
		seen.add(key)
	return gone


def tidy() -> None:
	"""Daily: thin each workbook's unnamed versions, and drop edits older than
	KEPT_DAYS that the oldest version already holds."""
	now = now_datetime()
	for workbook in frappe.get_all(VERSION, filters={"creation": ["<", now - timedelta(days=1)]}, pluck="workbook", distinct=True):
		rows = frappe.get_all(VERSION, filters={"workbook": workbook, "pinned": 0, "kind": "auto"}, fields=["name", "creation"])
		for name in thinned(rows, now):
			frappe.delete_doc(VERSION, name, ignore_permissions=True, force=True)
		oldest = frappe.get_all(VERSION, filters={"workbook": workbook}, fields=["seq"], order_by="seq asc", limit=1)
		if oldest:
			frappe.db.delete(CHANGE, {"workbook": workbook, "seq": ["<", oldest[0].seq], "creation": ["<", now - timedelta(days=KEPT_DAYS)]})
		frappe.db.commit()
