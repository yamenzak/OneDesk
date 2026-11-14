"""A second person: what waits for somebody other than the person who
asked. A payment out of the ordinary, a party's changed bank details and a
large export each make a Second Approval, which whoever may decide sees on
Home and is told of, and approves or refuses on its head. Nobody decides
their own and no agent decides any; where nobody else may, the person who
asked approves it alone, with remarks the record keeps. More in
one/AGENTS.md, Second approval."""

import frappe
from frappe import _
from frappe.utils import add_days, now_datetime

from onedesk.one import roles

DOCTYPE = "Second Approval"
WAITING, APPROVED, REFUSED = "Waiting", "Approved", "Refused"

APPROVE = {
	"Payment": "Approve Payment",
	"Bank Details": "Approve Bank Details",
	"Export": "Approve Export",
}
"""Each kind's one action, as its head and its notification name it."""

DONE = {"Payment": "onedesk.one_book.unusual.approved"}
"""What approving a kind does besides recording it: a payment is submitted
by whoever approved it."""

MACHINES = ("Administrator", "Guest")


def asker() -> str:
	"""Who asks: the person an agent or OneAI works for, else who is signed in."""
	return frappe.flags.one_intake_for or frappe.session.user


def machine(user: str | None = None) -> bool:
	"""Whether `user` is no person of the workspace: an agent, OneAI or
	Administrator. Without `user`, whoever acts now, which is OneAI too while
	it writes for somebody."""
	from onedesk.one.registry import agents
	from onedesk.one_ai.reading.act import AUTHOR

	if user is None:
		if frappe.flags.one_intake_writing:
			return True
		user = frappe.session.user
	return user in (*MACHINES, AUTHOR) or bool(agents.by_email(user))


def ask(kind: str, title: str, reasons: list[str] | str, role: str, keyed: dict, **values):
	"""The waiting request `keyed` names, made or brought up to date, and
	whether it is new: `keyed` are the fields that make it the same request
	(a payment's reference, a party, an export's record type and asker)."""
	reasons = "\n".join(reasons) if isinstance(reasons, list | tuple) else reasons
	held = frappe.db.get_value(DOCTYPE, {**keyed, "kind": kind, "status": WAITING}, "name")
	doc = frappe.get_doc(DOCTYPE, held) if held else frappe.new_doc(DOCTYPE)
	doc.update({**keyed, **values, "kind": kind, "title": title, "reasons": reasons, "approver_role": role, "status": WAITING})
	if not held:
		doc.asked_by = doc.get("asked_by") or asker()
		doc.asked_on = now_datetime()
	elif asker() not in (doc.asked_by, *_also(doc)):
		doc.also_asked_by = "\n".join([*_also(doc), asker()])
	doc.flags.ignore_permissions = True
	doc.save()
	return doc, not held


def withdraw(kind: str, keyed: dict) -> None:
	"""A waiting request that is no longer needed: its record changed so it
	no longer asks."""
	for name in frappe.get_all(DOCTYPE, filters={**keyed, "kind": kind, "status": WAITING}, pluck="name"):
		frappe.delete_doc(DOCTYPE, name, ignore_permissions=True, force=True)


def _also(doc) -> list[str]:
	"""Whoever else changed what a waiting request is about while it waited:
	they can't decide it either."""
	return [one for one in (doc.get("also_asked_by") or "").splitlines() if one]


def _holders(role: str) -> set[str]:
	return set(
		frappe.get_all(
			"Has Role",
			filters={"role": ["in", [role, roles.ADMINISTRATOR]], "parenttype": "User"},
			pluck="parent",
			distinct=True,
		)
	)


def deciders(doc) -> list[str]:
	"""Everybody but the person who asked who may decide it: enabled people
	holding its role or administering the workspace, never an agent."""
	held = _holders(doc.approver_role) - {doc.asked_by, *_also(doc)}
	people = frappe.get_all("User", filters={"name": ["in", sorted(held) or [""]], "enabled": 1, "user_type": "System User"}, pluck="name")
	return sorted(one for one in people if not machine(one))


def alone(doc) -> bool:
	"""Whether the person who asked is the only one who may decide it."""
	return not deciders(doc) and doc.asked_by in _holders(doc.approver_role)


def may_decide(doc, user: str | None = None) -> bool:
	if doc.status != WAITING or machine(user):
		return False
	user = user or frappe.session.user
	if user in _also(doc):
		return False
	if user == doc.asked_by:
		return alone(doc)
	return user in _holders(doc.approver_role)


def waiting_for(user: str) -> list[str]:
	"""The waiting requests `user` may decide, for Home."""
	if machine(user):
		return []
	held = set(frappe.get_roles(user))
	mine = roles.ADMINISTRATOR in held
	rows = frappe.get_all(DOCTYPE, filters={"status": WAITING}, fields=["name", "asked_by", "also_asked_by", "approver_role", "status"], limit=500)
	return [one.name for one in rows if (mine or one.approver_role in held) and may_decide(one, user)]


def _decide(name: str, status: str, remarks: str | None) -> object:
	doc = frappe.get_doc(DOCTYPE, name)
	if machine():
		frappe.throw(_("Only a person can approve or refuse this."), frappe.PermissionError)
	if not may_decide(doc):
		frappe.throw(_("Your role doesn't allow deciding this."), frappe.PermissionError)
	by_self = doc.asked_by == frappe.session.user
	if by_self and not (remarks or "").strip():
		frappe.throw(_("Remarks are required, since nobody else can approve this."))
	doc.update(
		{
			"status": status,
			"decided_by": frappe.session.user,
			"decided_on": now_datetime(),
			"alone": 1 if by_self else 0,
			"remarks": (remarks or "").strip() or None,
		}
	)
	doc.flags.ignore_permissions = True
	doc.save()
	return doc


def approve(name: str, remarks: str | None = None) -> str:
	"""Approve a waiting request and do what its kind does once approved."""
	doc = _decide(name, APPROVED, remarks)
	if doc.kind in DONE:
		frappe.get_attr(DONE[doc.kind])(doc)
	_told(doc)
	return _("{0} approved.").format(doc.title)


def refuse(name: str, remarks: str | None = None) -> str:
	doc = _decide(name, REFUSED, remarks)
	_told(doc)
	return _("{0} refused.").format(doc.title)


def _told(doc) -> None:
	if doc.asked_by == doc.decided_by or machine(doc.asked_by):
		return
	from onedesk.one import tell

	tell.approval_decided(doc)


def held(party_type: str | None, party: str | None) -> str | None:
	"""A party's last bank details change, while it waits or was refused:
	until it is approved, nothing is paid to them."""
	if not party_type or not party:
		return None
	last = frappe.get_all(
		DOCTYPE,
		filters={"kind": "Bank Details", "party_type": party_type, "party": party},
		fields=["name", "status"],
		order_by="creation desc",
		limit=1,
	)
	return last[0].name if last and last[0].status != APPROVED else None


def changed_since(party_type: str, party: str, days: int) -> bool:
	"""Whether a party's bank details changed in the last `days` days."""
	return bool(
		frappe.db.exists(
			DOCTYPE,
			{"kind": "Bank Details", "party_type": party_type, "party": party, "creation": [">=", add_days(now_datetime(), -days)]},
		)
	)


def masked(value: str | None) -> str:
	"""A bank number with all but its last four hidden. Pure."""
	value = "".join(str(value or "").split())
	if not value:
		return "—"
	return "•••• " + value[-4:] if len(value) > 4 else value


def query(user: str | None = None) -> str | None:
	"""permission_query_conditions: an administrator's are all; anybody
	else's are what they asked and what their roles decide."""
	user = user or frappe.session.user
	if user == "Administrator" or roles.administers(user):
		return None
	held = [frappe.db.escape(one) for one in frappe.get_roles(user)] or ["''"]
	return f"(`tabSecond Approval`.asked_by = {frappe.db.escape(user)} or `tabSecond Approval`.approver_role in ({', '.join(held)}))"


def has_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
	"""Read only: decided through `approve` and `refuse`, never by editing.
	The person who asked reads theirs, and so does whoever may decide it."""
	user = user or frappe.session.user
	if ptype not in ("read", "report", "print", None):
		return False
	if user == "Administrator" or roles.administers(user):
		return True
	return doc.asked_by == user or doc.approver_role in frappe.get_roles(user)
