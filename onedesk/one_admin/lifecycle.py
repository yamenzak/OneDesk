"""What starts a fall, and what stops one.

`ladder.py` decides *whether* a workspace should be on a different rung;
`steps.py` does the press and R2 work of getting it there. This is the part in
between: the events that put a workspace on the ladder in the first place, the
nightly walk, and the one call that takes it off.

**Nothing here talks to press.** Every rung is a job, for the reason every other
press call is a job: press is another service and it will be slow, down, or
mid-deploy exactly when the cron fires. A fall that failed half way is a job an
operator can see and resume, rather than a workspace in a state nobody wrote
down.

**One rung a night.** `nightly` moves a workspace one step and no further, even
when the clock says it is three rungs late. Each rung does real work and the
next one should start from a finished previous one; and a workspace that is
being suspended tonight and archived tomorrow gives whoever is watching a day to
notice. A workspace nobody has looked at for a year still gets there, just not
in one go.

**Falling is never retroactive.** A workspace goes Overdue when a payment fails
and not a day earlier, so `status_since` is written when the rung is reached.
The one thing this costs: an operator who fixes a stuck job has reset the clock
on that rung, which is the forgiving direction.
"""

import frappe
from frappe.utils import now_datetime

from onedesk.one_admin import ladder, runner, site

#: What to call the job that gets a workspace to each rung.
BY = {
	"Overdue": None,  # nothing to do to the site; the fall is the record of it
	"Suspended": "Suspend",
	"Archived": "Archive",
	"Dropped": "Drop",
	"Live": "Restore",
}

#: Workspaces looked at per nightly run. High enough that a real estate of
#: tenants is walked in one night, low enough that a bug does not archive the
#: whole book before anybody wakes up.
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
	_arrive(tenant, "Overdue", "a payment failed")
	return "Overdue"


def paid(tenant) -> str | None:
	"""Money arrived. Climb.

	From Overdue this is a field; from Suspended it is a job, because press has
	to be asked to serve the site again. From Archived it refuses: the site was
	destroyed, and putting a new one in its place from a backup is somebody's
	decision rather than a webhook's.
	"""
	if tenant.status == "Live":
		return None
	if tenant.status == "Archived":
		frappe.throw(
			frappe._(
				"{0} was archived. Its site has to be rebuilt from the backup before it can"
				" be live again, and that is not something a payment does on its own."
			).format(tenant.name)
		)
	rung = ladder.climbing(tenant.status)
	if tenant.status == "Overdue":
		_arrive(tenant, rung, "paid")
		return rung
	return _job(tenant, rung)


def fall(tenant, rung: str | None = None) -> str | None:
	"""Move one rung down, doing whatever that rung needs.

	`rung` is for an operator doing it by hand. Left out, the clock decides, and
	a workspace that is not due stays where it is.
	"""
	rung = rung or ladder.due(tenant.status, tenant.status_since, now_datetime(), _days())
	if rung is None:
		return None
	if rung != ladder.below(tenant.status):
		frappe.throw(
			frappe._("{0} is on {1} and the rung below it is not {2}.").format(
				tenant.name, tenant.status, rung
			)
		)
	if BY.get(rung) is None:
		_arrive(tenant, rung, "the clock")
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
		"since": str(tenant.status_since) if tenant.status_since else None,
		# How long this rung lasts, so a screen drawing a bar has a denominator
		# without keeping its own copy of the periods. A second copy in
		# JavaScript is a second copy to be wrong the day somebody lengthens the
		# grace period because of an outage.
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
