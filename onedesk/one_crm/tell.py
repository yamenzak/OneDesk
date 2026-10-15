"""What OneCRM tells people: the next step on a lead or an opportunity come
due, to its owner. Every notification's words are its file in
notifications/one_crm/."""

from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import now_datetime

from onedesk.one import notify
from onedesk.one_crm.next import OPEN, OWNER

#: How often the scheduler looks for steps come due (hooks.py).
EVERY = timedelta(minutes=5)


def due() -> None:
	"""Every five minutes: tell each owner of an open lead or opportunity whose
	next step has come due since the last look, once."""
	now = now_datetime()
	for doctype, owner in OWNER.items():
		for one in frappe.get_all(
			doctype,
			filters=[
				["status", "in", OPEN[doctype]],
				["one_next_on", ">", now - EVERY * 2],
				["one_next_on", "<=", now],
				[owner, "is", "set"],
			],
			fields=[
				"name",
				"title" if doctype == "Opportunity" else "lead_name as title",
				owner,
				"one_next_step",
				"one_next_on",
			],
		):
			key = f"one_crm:due:{doctype}:{one.name}:{one.one_next_on}"
			if frappe.cache.get_value(key):
				continue
			frappe.cache.set_value(key, 1, expires_in_sec=86400)
			notify.notify(
				"Next Step Due",
				one.get(owner),
				record=(doctype, one.name),
				sender="Administrator",
				step=one.one_next_step or _("Next Step"),
				title=one.title or one.name,
			)
