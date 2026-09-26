"""What the workspace's own account says above its fields. See one/head.py.

Everything on it is a copy of what the administrator said (account.py), so
it opens on where the workspace stands, one sentence when money or a lost
connection is the news, and what it stores against what its plan allows.
Its buttons are dialogs that ask questions (a domain checked against DNS, a
credit pack) and stay in workspace_account.js.
"""

from frappe import _, _lt
from frappe.utils import flt

#: The workspace's standing in a word, and its colour.
SAYS = {
	"Requested": ("orange", _lt("Being set up")),
	"Provisioning": ("blue", _lt("Being set up")),
	"Live": ("green", _lt("Active")),
	"Overdue": ("orange", _lt("Payment overdue")),
	"Suspended": ("red", _lt("Suspended")),
	"Archived": ("grey", _lt("Archived")),
}


def size(count) -> str:
	"""Bytes as a person reads them, in thousands as a disk is sold: desk.js's
	`onedesk.tenant.size`, so the two say a size the same way."""
	left = flt(count)
	if not left:
		return _("nothing")
	units = ("B", "KB", "MB", "GB", "TB")
	at = 0
	while left >= 1000 and at < len(units) - 1:
		left /= 1000
		at += 1
	return f"{round(left) if left >= 10 or at == 0 else f'{left:.1f}'} {units[at]}"


def account_state(doc):
	if not doc.get("status"):
		return None
	colour, word = SAYS.get(doc.status, ("grey", doc.status))
	return {"label": str(word), "colour": colour}


def account_said(doc):
	"""The money one wins. A workspace about to be suspended has to be told
	how long it has; that the account could not be reached is worth saying,
	but not instead."""
	if doc.get("owing") and doc.get("next_status"):
		left = doc.get("days_left")
		return {
			"text": _("Payment overdue. This workspace is suspended tonight.")
			if left == 0
			else _("Payment overdue. This workspace is suspended in {0} days.").format(left),
			"colour": "red" if left is not None and left <= 2 else "orange",
		}
	if doc.get("last_error"):
		return {"text": _("Could not reach your account. Showing what was last known."), "colour": "orange"}
	return None


def account_storage(doc):
	"""What it stores against what its plan allows, in red when over."""
	limit, used = flt(doc.get("storage_limit")), flt(doc.get("storage_bytes"))
	if limit <= 0:
		return None
	return {
		"value": _("{0} of {1}").format(size(used), size(limit)),
		"tone": "alarm" if used > limit else None,
		"meter": {"value": min(used, limit), "of": limit},
	}


MEASURES = {
	"account.state": account_state,
	"account.said": account_said,
	"account.storage": account_storage,
}

HEADS = [
	{
		"doctype": "Workspace Account",
		"indicators": [{"label": _lt("Standing"), "measure": "account.state"}],
		"sentences": [{"measure": "account.said"}],
		"band": [{"label": _lt("Storage"), "source": "Measure", "measure": "account.storage"}],
	},
]
