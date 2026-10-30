"""Boards: things whose state or value people change by hand, shown live on
screens (D5 of SCRATCHPAD.md). A board has items, the business's own
states (each with a colour and an optional time limit) and/or a value per
item. It is changed from Boards on a phone or a tablet, one item's buttons
behind a QR code; every change is kept (Display Board Change), wakes the
screens, and a state kept past its limit is told once. Nothing here names a
trade: an operating room, a bay, a score and a dish of the day are all set
up as boards."""

from typing import Annotated

import frappe
from frappe import _
from frappe.utils import cint, flt, get_datetime, now_datetime, time_diff_in_seconds

from onedesk.one_display import live

DOCTYPE = "Display Board"
CHANGE = "Display Board Change"
EVENT = "onedesk_board"


def may(board) -> bool:
	"""Whether the person may change the board: one of its people, or, when
	it names nobody, anyone with OneDisplay."""
	doc = board if not isinstance(board, str) else frappe.get_cached_doc(DOCTYPE, board)
	user = frappe.session.user
	if "Workspace Administrator" in frappe.get_roles():
		return True
	people = [row.user for row in doc.people]
	if people:
		return user in people
	return bool({"OneDisplay User", "OneDisplay Manager"} & set(frappe.get_roles()))


def _item(doc, item: str):
	found = next((row for row in doc.items if row.item_name == item), None)
	if not found:
		frappe.throw(_("{0} is not on {1}.").format(item, doc.board_name), frappe.DoesNotExistError)
	return found


def _state(doc, state: str | None):
	return next((row for row in doc.states if row.state == state), None)


def shown(doc) -> dict:
	"""A board as a screen and the control page draw it."""
	at = now_datetime()
	items = []
	for row in doc.items:
		state = _state(doc, row.state)
		minutes = max(0, time_diff_in_seconds(at, row.since) / 60) if row.since else None
		limit = cint(state.limit_minutes) if state else 0
		items.append(
			{
				"item": row.item_name,
				"state": row.state or "",
				"colour": (state.colour if state else "") or "",
				"value": row.value or "",
				"since": int(get_datetime(row.since).timestamp() * 1000) if row.since else None,
				"minutes": round(minutes, 1) if minutes is not None else None,
				"limit": limit or None,
				"over": 1 if limit and minutes is not None and minutes > limit else 0,
			}
		)
	return {
		"board": doc.name,
		"value_label": doc.value_label or "",
		"value_kind": doc.value_kind or "Number",
		"states": [{"state": row.state, "colour": row.colour or "", "limit": cint(row.limit_minutes) or None} for row in doc.states],
		"items": items,
	}


def rows(board: str) -> list[dict]:
	"""A Board source's rows (sources.py): one for each item."""
	if not frappe.db.exists(DOCTYPE, board):
		return []
	return shown(frappe.get_cached_doc(DOCTYPE, board))["items"]


@frappe.whitelist()
def mine() -> list[dict]:
	"""The boards the person may change, for Boards' picker."""
	out = []
	for name in frappe.get_all(DOCTYPE, pluck="name", order_by="board_name asc"):
		doc = frappe.get_cached_doc(DOCTYPE, name)
		if may(doc):
			out.append({"board": name, "description": doc.description or "", "items": len(doc.items)})
	return out


@frappe.whitelist()
def get(board: Annotated[str, "The board."]) -> dict:
	"""A board with each item's state, value and time in it."""
	doc = frappe.get_doc(DOCTYPE, board)
	if not may(doc):
		frappe.throw(_("You may not change {0}.").format(board), frappe.PermissionError)
	return shown(doc)


def _changed(doc, row, state: str | None, value: str | None) -> None:
	"""One change, kept and told: the item's row written, the change logged
	with how long it was in what it was, and the screens woken."""
	at = now_datetime()
	was_state, was_value = row.state or "", row.value or ""
	minutes = time_diff_in_seconds(at, row.since) / 60 if row.since else 0
	values = {}
	if state is not None and state != was_state:
		values.update(state=state, since=at, told=0)
	if value is not None and value != was_value:
		values["value"] = value
	if not values:
		return
	frappe.db.set_value("Display Board Item", row.name, values, update_modified=False)
	frappe.get_doc(
		{
			"doctype": CHANGE,
			"board": doc.name,
			"item": row.item_name,
			"state": values.get("state", was_state),
			"was_state": was_state,
			"minutes": round(minutes, 1) if "state" in values else 0,
			"value": values.get("value", was_value),
			"was_value": was_value,
			"changed_by": frappe.session.user,
		}
	).insert(ignore_permissions=True)
	frappe.clear_document_cache(DOCTYPE, doc.name)
	frappe.publish_realtime(EVENT, {"board": doc.name}, after_commit=True)
	live.wake()


@frappe.whitelist(methods=["POST"])
def change(
	board: Annotated[str, "The board."],
	item: Annotated[str, "The item on it."],
	state: Annotated[str | None, "Its new state, one of the board's."] = None,
	value: Annotated[str | None, "Its new value."] = None,
	step: Annotated[float | None, "Added to a number value, such as 1 or -1."] = None,
) -> dict:
	"""Set an item's state, its value, or step its value up or down."""
	doc = frappe.get_doc(DOCTYPE, board)
	if not may(doc):
		frappe.throw(_("You may not change {0}.").format(board), frappe.PermissionError)
	row = _item(doc, item)
	if state is not None and state != "" and not _state(doc, state):
		frappe.throw(_("{0} is not a state of {1}.").format(state, doc.board_name))
	if step is not None:
		value = _stepped(row.value, flt(step))
	if value is not None:
		value = str(value).strip()[:140]
	_changed(doc, row, state, value)
	return shown(frappe.get_doc(DOCTYPE, board))


def _stepped(value, step: float) -> str:
	"""A number value moved by a step, kept whole when it is. Pure."""
	moved = flt(value) + step
	return str(int(moved)) if moved == int(moved) else str(round(moved, 2))


@frappe.whitelist()
def codes(board: Annotated[str, "The board."]) -> list[dict]:
	"""A QR code for each item, which opens that item's buttons in Boards."""
	from urllib.parse import urlencode

	from onedesk.one import qr

	doc = frappe.get_doc(DOCTYPE, board)
	doc.check_permission("read")
	out = []
	for row in doc.items:
		link = frappe.utils.get_url("/desk/boards?" + urlencode({"board": doc.name, "item": row.item_name}))
		out.append({"item": row.item_name, "link": link, "svg": qr.svg(link)})
	return out


def overdue() -> list[tuple]:
	"""Each item kept in a state past its limit and not yet told, as (board,
	item row, minutes), marked told: tell.past_limits says so."""
	at = now_datetime()
	out = []
	for name in frappe.get_all(DOCTYPE, pluck="name"):
		doc = frappe.get_doc(DOCTYPE, name)
		limits = {row.state: cint(row.limit_minutes) for row in doc.states if cint(row.limit_minutes)}
		for row in doc.items:
			limit = limits.get(row.state)
			if not limit or not row.since or row.told:
				continue
			minutes = time_diff_in_seconds(at, row.since) / 60
			if minutes > limit:
				frappe.db.set_value("Display Board Item", row.name, "told", 1, update_modified=False)
				out.append((doc, row, minutes))
	return out


def history(board: str, item: str | None = None, limit: int = 200) -> list[dict]:
	"""The board's changes, newest first, with how long each state lasted."""
	filters = {"board": board, **({"item": item} if item else {})}
	return frappe.get_all(
		CHANGE,
		filters=filters,
		fields=["item", "was_state", "state", "minutes", "was_value", "value", "changed_by", "creation"],
		order_by="creation desc",
		limit=limit,
	)
