"""What starts a fall, and what stops one.

Between `ladder.py` (whether) and `steps.py` (the work): the events that put a
workspace on the ladder, the nightly walk of one rung, and the call that takes
it off. Nothing here talks to press.
"""

import frappe
from frappe.utils import now_datetime

from onedesk.one_admin import ladder, log, runner, site

BY = {
	"Overdue": None,
	"Suspended": "Suspend",
	"Archived": "Archive",
	"Dropped": "Drop",
	"Live": "Restore",
}

AT_A_TIME = 50


def owed(tenant) -> str | None:
	"""A payment failed. Start the fall, unless it has already started.

	Idempotent because Stripe will send this more than once: a subscription
	retries its invoice on a schedule of its own, and each retry that fails is
	another event. A workspace already on the ladder stays where it is, with the
	clock it already has — a second failure is not a reason to start the grace
	period again.
	"""
	if tenant.status != "Live":
		return None
	_arrive(tenant, "Overdue", log.said("owed"))
	return "Overdue"


def paid(tenant) -> str | None:
	"""Money arrived. Climb.

	From Overdue this is a field; from Suspended it is a job, because press has
	to be asked to serve the site again. Once the site may be gone (Archived,
	Dropped, or an Archive job past its first step) the operators are told
	(Paid While Archived) instead. A workspace being built has nothing to climb.
	"""
	if tenant.status == "Live" or tenant.get("is_test"):
		return None
	if tenant.status in ("Archived", "Dropped") or archiving(tenant.name):
		from onedesk.one_admin import tell

		tell.paid_while_archived(tenant)
		return None
	rung = ladder.climbing(tenant.status)
	if rung is None:
		return None
	if tenant.status == "Overdue":
		_arrive(tenant, rung, log.said("paid"))
		return rung
	return _job(tenant, rung)


def ended(tenant) -> str | None:
	"""Its subscription was cancelled in Stripe, so nothing will bill it again.

	A Live workspace starts the fall at Overdue, as an unpaid one does, unless
	it is already going: a closing day was asked for, or an Archive job (whose
	`stop_billing` is what cancelled it) is running.
	"""
	if tenant.status != "Live" or tenant.get("closing_on") or _open(tenant.name, "Archive"):
		return None
	_arrive(tenant, "Overdue", log.said("cancelled"))
	return "Overdue"


def archiving(slug: str) -> bool:
	"""Whether an Archive job has got past its first step, after which the
	site may be gone and only a person brings it back."""
	from onedesk.one_admin import steps

	return any(one.step != steps.WALKS["Archive"][0] for one in _open(slug, "Archive"))


def _open(slug: str, kind: str) -> list:
	return frappe.get_all(
		"Provisioning Job",
		filters={"tenant": slug, "kind": kind, "status": ["in", ("Pending", "Waiting")]},
		fields=["name", "step"],
	)


def fall(tenant, rung: str | None = None, why: str | None = None) -> str | None:
	"""Move one rung down, doing whatever that rung needs.

	`rung` is for an operator doing it by hand, who may also archive a build
	that failed (ladder.by_hand). Left out, the clock decides, and a workspace
	that is not due stays where it is. A test workspace stays Live.
	"""
	from onedesk.one_admin import testbed

	testbed.refuse(tenant, "moved")
	rung = rung or ladder.due(tenant.status, tenant.status_since, now_datetime(), _days())
	if rung is None:
		return None
	if rung != ladder.by_hand(tenant.status):
		frappe.throw(
			frappe._("{0} is {1} and can't move to {2}.").format(
				tenant.name, tenant.status, rung
			)
		)
	if BY.get(rung) is None:
		_arrive(tenant, rung, why or log.said("clock"))
		return rung
	return _job(tenant, rung)


def nightly() -> None:
	"""Walk everybody who is late, one rung each.

	Never raises on one workspace's account: a tenant whose fall throws must not
	stop the others, and a stuck one is a log entry somebody reads rather than a
	queue that stopped.
	"""
	if not site.is_admin():
		return
	now = now_datetime()
	days = _days()
	for slug in _on_the_ladder():
		try:
			tenant = frappe.get_doc("Tenant", slug)
			if ladder.due(tenant.status, tenant.status_since, now, days):
				fall(tenant)
		except Exception:
			frappe.log_error(title=f"The ladder, at {slug}")
			frappe.db.rollback()


def standing(tenant) -> dict:
	"""What the workspace is told about where it stands.

	Returned by the proxy so a tenant's own header can say it, which is the only
	warning most customers will read. `days_left` is None rather than zero when
	nothing is going to happen, because those are different sentences.
	"""
	days = _days()
	return {
		"owing": ladder.owing(tenant.status),
		"rung": tenant.status,
		"next": ladder.below(tenant.status),
		"since": str(tenant.status_since) if tenant.status_since else None,
		"days": days.get(tenant.status),
		"days_left": ladder.days_left(tenant.status, tenant.status_since, now_datetime(), days),
	}


def _on_the_ladder() -> list[str]:
	"""Only the rungs a clock can move, and only the ones with a clock on them.

	Live is excluded because nothing but a payment failing moves a workspace off
	it, and Dropped because there is nowhere below.
	"""
	return frappe.get_all(
		"Tenant",
		filters={
			"status": ["in", [rung for rung in ladder.RUNGS if rung not in ("Live", "Dropped")]],
			"status_since": ["is", "set"],
		},
		order_by="status_since asc",
		limit=AT_A_TIME,
		pluck="name",
	)


def _job(tenant, rung: str) -> str:
	"""Queue the work that gets to a rung. The runner writes the status."""
	runner.start(tenant.name, BY[rung])
	return rung


def _arrive(tenant, rung: str, why: str) -> str:
	"""A rung that needs nothing done to the site, written here rather than by a step."""
	from onedesk.one_admin import steps

	steps._arrive(tenant, rung, why)
	return rung


def _days() -> dict:
	"""The periods, as an operator set them.

	Read every time rather than cached: somebody lengthening the grace period
	because of an outage wants it to apply tonight, not after a restart.
	"""
	held = frappe.get_cached_doc("One Admin Settings")
	return {
		"Overdue": held.grace_days if held.grace_days is not None else ladder.DAYS["Overdue"],
		"Suspended": held.held_days if held.held_days is not None else ladder.DAYS["Suspended"],
		"Archived": held.kept_days if held.kept_days is not None else ladder.DAYS["Archived"],
	}
