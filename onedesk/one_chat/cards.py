"""An agent's Draft and Ask First, as a card in the conversation between
the agent and the person it asks (docs/ARC-AI.md, OneChat). The card is
the Reading Action the door wrote (one_ai/agents/door.py), read as it
stands now; Approve is the door's own approval (reading/act.py settle), so
nothing here decides or writes a record itself. Change edits what the card
proposes before it is approved, under the same rule as Approve: only the
person asked, or an administrator."""

import json
from contextlib import contextmanager

import frappe
from frappe import _

from onedesk.one_chat import agents, channels, messages

SHOWN = ("Proposed", "Done")
FIELDS = 8
PLAIN = (str, int, float, bool, type(None))


def posted(doc, method=None) -> None:
	"""doc_event, Reading Action after_insert: an agent's draft or question
	lands in its conversation with the person it acted for. Never stops the
	door: a card that cannot be posted is logged."""
	app = agents.of_user(doc.agent)
	if not app or doc.level not in SHOWN or not doc.on_behalf_of:
		return
	try:
		with _as(doc.on_behalf_of):
			channel = frappe.get_doc("Chat Channel", channels.last_with(app, doc.on_behalf_of) or channels.with_agent(app, doc.on_behalf_of).name)
		messages.post(channel, said(doc), sender=agents.user_of(app), agent=app, action=doc.name)
	except Exception:
		frappe.log_error(title="OneChat could not post an agent's card", reference_doctype="Reading Action", reference_name=doc.name)


@contextmanager
def _as(user: str):
	was = frappe.session.user
	frappe.set_user(user)
	try:
		yield
	finally:
		frappe.set_user(was)


def said(row) -> str:
	"""The card's one line: what the agent did or asks."""
	what = _(row.target_doctype or "")
	if row.level == "Done":
		return _("Drafted {0} {1}.").format(what, row.target_name or "").strip()
	return _("Approve this {0}?").format(what) if row.kind == "Create" else _("Approve this change to {0} {1}?").format(what, row.target_name or "")


def card(name: str) -> dict:
	"""A card as it stands: the action, its level and the values it proposes."""
	row = frappe.get_doc("Reading Action", name)
	try:
		values = json.loads(row.after or "{}")
	except ValueError:
		values = {}
	meta = frappe.get_meta(row.target_doctype) if row.target_doctype else None
	return {
		"name": row.name,
		"kind": row.kind,
		"level": row.level,
		"doctype": row.target_doctype,
		"record": row.target_name,
		"why": row.why or "",
		"asked": row.on_behalf_of,
		"fields": [{**one, "label": _(meta.get_label(one["fieldname"]))} for one in shown_values(values)] if meta else shown_values(values),
		"may_decide": _may(row),
	}


def shown_values(values: dict) -> list[dict]:
	"""The plain values a card shows and Change edits; tables are left to
	the record. Pure."""
	return [
		{"fieldname": key, "value": value}
		for key, value in (values or {}).items()
		if isinstance(value, PLAIN) and not key.startswith("_") and key != "doctype"
	][:FIELDS]


def changed(values: dict, edits: dict) -> dict:
	"""The proposed values with a person's edits to plain fields it already
	had; nothing new is added and no table is touched. Pure."""
	kept = dict(values or {})
	for key, value in (edits or {}).items():
		if key in kept and isinstance(kept[key], PLAIN) and isinstance(value, PLAIN):
			kept[key] = value
	return kept


def approve(name: str) -> dict:
	"""Approve, through the door's approval (act.settle), which checks who
	may decide and that they may do it themselves."""
	from onedesk.one_ai.reading import act

	reach(name)
	done = act.settle(name, 1)
	_told(name)
	return done


def dismiss(name: str) -> dict:
	from onedesk.one_ai.reading import act

	reach(name)
	done = act.settle(name, 0)
	_told(name)
	return done


def change(name: str, edits: dict | str) -> dict:
	from onedesk.one_ai.reading import act

	row = frappe.get_doc("Reading Action", name)
	reach(name)
	act._may_decide(row)
	if row.level != "Proposed":
		frappe.throw(_("This was already {0}.").format(_(row.level).lower()))
	edits = frappe.parse_json(edits) if isinstance(edits, str) else edits
	row.db_set("after", json.dumps(changed(json.loads(row.after or "{}"), edits or {}), default=str))
	_told(name)
	return card(name)


def reach(name: str) -> None:
	"""A card is read and answered from a conversation the reader is in."""
	held = frappe.get_all("Chat Message", filters={"action": name}, pluck="channel", limit=1)
	if not held:
		frappe.throw(_("This card isn't in any conversation."), frappe.PermissionError)
	channels.opened(held[0])


def _told(name: str) -> None:
	for message in frappe.get_all("Chat Message", filters={"action": name}, pluck="name"):
		messages.live(frappe.get_doc("Chat Message", message), messages.CHANGED)


def _may(row) -> bool:
	from onedesk.one.roles import administers

	return frappe.session.user == row.on_behalf_of or administers()
