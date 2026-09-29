"""The log: one row for each thing that happened to a workspace.

Every row is written here, and each says three things the list used to leave
out. **Who**: the customer (a plan they changed, through the proxy), an
operator (a button they pressed, or a job they started), or One (the clock, a
payment, a nightly measure). **Which job**, when a job did it. And **what**, in
words: a fixed phrase from `SAID`, which is `_lt` so the list shows it in the
operator's own language, or plain data (a plan's name, two sizes) that needs
none.

The workspace's own Activity shows its rows too (`timeline`, frappe's
`additional_timeline_content`), so its story is on its form.
"""

import frappe
from frappe import _, _lt
from frappe.utils import escape_html

from onedesk.one_admin import site

#: What a row may say in words. Written as the English, and shown translated.
SAID = {
	"owed": _lt("A payment failed"),
	"paid": _lt("Paid"),
	"clock": _lt("Its time on the last rung ran out"),
	"by_hand": _lt("Moved by hand"),
	"stopped": _lt("Frappe Cloud stopped serving the site"),
	"archived": _lt("The site was deleted and a backup kept; the files were kept"),
	"dropped": _lt("The files were deleted"),
}

#: Over storage is written again only when it has grown or shrunk this much,
#: or a month has passed, rather than every night it stays over.
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

	from onedesk.one.heads import size

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
