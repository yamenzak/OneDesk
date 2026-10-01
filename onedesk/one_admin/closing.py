"""A workspace closed because the person who pays for it asked.

The workspace asks (one/closing.py, through the proxy); this writes the day
and walks it there. Closing is the ladder's own Archive job, started by a
date rather than by a debt, so it takes the same backup, cancels the same
subscription and is undone the same way; and from Archived it falls to
Dropped on the ladder's own clock, which is the day it is deleted for good.

**Notice, not at once.** It closes `NOTICE_DAYS` after it is asked, and
works as before until then: long enough to take the full download, tell
everybody and move what they need. Until that day the same person may keep
it open; after it, the site is gone and restoring it from the backup is an
operator's decision, as for an archived workspace that pays.

**Billing.** Asking sets the subscription to end with its period, so no
renewal falls in the notice; the Archive job cancels it outright. What was
paid for the current period is not refunded, as the Terms say.
"""

import frappe
from frappe.utils import add_days, getdate, today

from onedesk.one_admin import faults, lifecycle, log, runner
from onedesk.one_admin.ladder import NOTICE_DAYS

#: The rungs a workspace may be asked to close from: the ones still served.
OPEN = ("Live", "Overdue")


def when(tenant) -> dict:
	"""The closing day and the deletion day, for the workspace to show.
	Empty when nobody asked."""
	if not tenant.get("closing_on"):
		return {}
	days = lifecycle._days()
	closes = getdate(tenant.closing_on)
	if tenant.status == "Archived" and tenant.status_since:
		closes = getdate(tenant.status_since)
	kept = days.get("Archived")
	return {
		"closing_on": str(closes),
		# A period of zero means never (ladder.py), so there is no day to say.
		"deleted_on": str(add_days(closes, kept)) if kept else None,
		"asked_by": tenant.closing_asked_by,
		"closed": tenant.status in ("Archived", "Dropped"),
	}


def ask(slug: str, by: str) -> dict:
	"""Close it in `NOTICE_DAYS`. Asked twice, the first day stands."""
	tenant = frappe.get_doc("Tenant", slug)
	if tenant.status not in OPEN:
		raise faults.Refused(f"{slug} is {tenant.status} and cannot be closed from here")
	if tenant.is_house:
		raise faults.Refused("The house workspace is not closed from inside it")
	if tenant.closing_on:
		return when(tenant)
	on = add_days(today(), NOTICE_DAYS)
	tenant.db_set({"closing_on": on, "closing_asked_by": by}, notify=True)
	_renewal(tenant, ends=True)
	log.write(slug, "Closing Asked", by, by="Customer")
	from onedesk.one_admin import tell

	tell.closing(tenant)
	return when(tenant)


def keep(slug: str, by: str) -> dict:
	"""Changed their mind before the day: it stays open and billed."""
	tenant = frappe.get_doc("Tenant", slug)
	if not tenant.closing_on:
		return {}
	if tenant.status not in OPEN:
		raise faults.Refused(f"{slug} has closed; ask us to restore it from its backup")
	tenant.db_set({"closing_on": None, "closing_asked_by": None}, notify=True)
	_renewal(tenant, ends=False)
	log.write(slug, "Closing Withdrawn", by, by="Customer")
	return {}


def _renewal(tenant, ends: bool) -> None:
	"""The subscription ends with its period, or renews again. A workspace
	with none (a trial, the house) has nothing to change."""
	if not tenant.get("stripe_subscription"):
		return
	from onedesk.one_admin import stripe

	try:
		stripe.at_period_end(tenant.stripe_subscription, ends)
	except faults.Refused:
		# The Archive job cancels it either way; an operator sees the log.
		frappe.log_error(title=f"Closing {tenant.name}: the subscription was not changed")


def due() -> None:
	"""Daily: every workspace whose closing day has come is archived."""
	from onedesk.one_admin import site

	if not site.is_admin():
		return
	for slug in frappe.get_all(
		"Tenant",
		# "is set" first: frappe reads a missing date as 0001-01-01, which is
		# before today, so without it every workspace would be closed.
		filters=[
			["closing_on", "is", "set"],
			["closing_on", "<=", today()],
			["status", "in", list(OPEN)],
		],
		pluck="name",
		limit=lifecycle.AT_A_TIME,
	):
		try:
			runner.start(slug, "Archive")
		except Exception:
			frappe.log_error(title=f"Closing {slug}")
			frappe.db.rollback()
