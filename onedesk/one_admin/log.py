"""The log: one row for each thing that happened to a workspace.

Every row is written here, and says who, which job, and what, in words.
"""

import frappe
from frappe import _, _lt
from frappe.utils import escape_html

from onedesk.one_admin import site

SAID = {
	"owed": _lt("A payment failed"),
	"cancelled": _lt("Its subscription was cancelled in Stripe"),
	"paid": _lt("Paid"),
	"clock": _lt("Grace period ended"),
	"by_hand": _lt("Set by an operator"),
	"stopped": _lt("Frappe Cloud stopped serving the site"),
	"archived": _lt("Site deleted after a backup. Files kept."),
	"dropped": _lt("Files deleted"),
}

AGAIN_BYTES = 10**9
AGAIN_DAYS = 30


def said(key: str) -> str:
	"""A fixed phrase's English, which is what is stored and what the list
	translates."""
	return SAID[key].msg


def write(tenant: str, kind: str, detail: str = "", by: str | None = None, job=None, amount=None) -> None:
	"""One row. `by` is Customer when the caller knows it was them; otherwise
	it is the operator whose button or job it was, or One."""
	user = (job.owner if job is not None else None) or frappe.session.user
	operator = user not in ("Administrator", "Guest") and site.OPERATOR in frappe.get_roles(user)
	frappe.get_doc(
		{
			"doctype": "Tenant Event",
			"tenant": tenant,
			"kind": kind,
			"detail": detail,
			"by": by or ("Operator" if operator else "One"),
			"by_user": user if (by or "Operator") == "Operator" and operator else None,
			"job": job.name if job is not None else None,
			"amount": amount,
		}
	).insert(ignore_permissions=True)


def over_storage(tenant: str, held: int, limit: int) -> None:
	"""Over its storage: written when it first goes over, then only when it
	has moved by a gigabyte or a month has passed."""
	from frappe.utils import add_days, now_datetime

	from onedesk.one_account.heads import size

	last = frappe.get_all(
		"Tenant Event",
		filters={"tenant": tenant, "kind": "Over Storage"},
		fields=["amount", "creation"],
		order_by="creation desc",
		limit=1,
	)
	if (
		last
		and abs(int(last[0].amount or 0) - held) < AGAIN_BYTES
		and last[0].creation > add_days(now_datetime(), -AGAIN_DAYS)
	):
		return
	write(tenant, "Over Storage", f"{size(held)} / {size(limit)}", amount=held)


def timeline(doctype: str, docname: str) -> list[dict]:
	"""additional_timeline_content for Tenant: its log in its Activity."""
	rows = frappe.get_all(
		"Tenant Event",
		filters={"tenant": docname},
		fields=["kind", "detail", "by", "by_user", "creation"],
		order_by="creation desc",
		limit=100,
	)
	return [
		{
			"icon": "history",
			"creation": one.creation,
			"content": " · ".join(
				filter(
					None,
					[
						f"<strong>{escape_html(_(one.kind))}</strong>",
						escape_html(_(one.detail)) if one.detail else "",
						escape_html(_who(one)),
					],
				)
			),
		}
		for one in rows
	]


def _who(row) -> str:
	if row.by == "Operator" and row.by_user:
		return _("by {0}").format(frappe.utils.get_fullname(row.by_user))
	if row.by == "Customer":
		return _("by the customer")
	return _("by One")
