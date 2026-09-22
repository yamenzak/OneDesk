"""Driving a Provisioning Job forward, on a cron rather than in a request.

A site takes minutes to build. Doing that inline would hold a worker open for
the whole of it and lose the lot to a restart, so the request creates a job and
returns, and this walks it.

**A job resumes; it never repeats.** The step it is on is a field, so a worker
that died between two steps comes back to the second one. Every step is written
to be safe run twice anyway — see `steps.py` — because the field is written
after the step returns and a crash in that gap is real.

**Backoff is per step and grows.** A site press has not finished building is
worth asking about again in a few seconds; a call that failed for a reason we
cannot see is worth leaving longer each time. The cap stops a stuck job from
being asked about once a day and finishing a week late.
"""

import frappe
from frappe.utils import add_to_date, now_datetime

from onedesk.one_admin import faults, site, steps

#: Seconds before the next attempt, by attempt number. The last is the cap.
BACKOFF = (10, 30, 60, 120, 300)

#: Attempts at one step before it is somebody's problem rather than the cron's.
#: High enough to ride out a press deploy, low enough that a genuinely stuck job
#: surfaces the same morning.
GIVE_UP_AFTER = 12

#: Jobs per cron tick. A tick that tried to finish everything would hold one
#: worker for as long as the slowest press call in the queue.
AT_A_TIME = 5


def tick() -> None:
	"""The cron entry. Never raises: one bad job must not stop the queue."""
	if not site.is_admin():
		return
	for name in _due():
		try:
			advance(name)
		except Exception:
			frappe.log_error(title=f"Provisioning {name}")
			frappe.db.rollback()


def _due() -> list[str]:
	return frappe.get_all(
		"Provisioning Job",
		filters={
			"status": ["in", ("Pending", "Waiting")],
			"next_run_at": ["<=", now_datetime()],
		},
		order_by="next_run_at asc",
		limit=AT_A_TIME,
		pluck="name",
	)


def advance(name: str) -> str:
	"""Run one step of one job and record what happened.

	Returns the job's status afterwards, so a caller driving this by hand — an
	operator, or a test — can loop until it stops changing.
	"""
	job = frappe.get_doc("Provisioning Job", name)
	if job.status in ("Done", "Failed"):
		return job.status

	step = job.step or steps.ORDER[0]
	tenant = frappe.get_doc("Tenant", job.tenant)

	try:
		waiting = getattr(steps, step)(job, tenant) == steps.WAIT
	except faults.Refused as refused:
		if isinstance(refused, faults.Again):
			return _later(job, str(refused))
		return _stop(job, tenant, str(refused))

	if waiting:
		return _later(job, None)
	return _next(job, tenant, step)


def _next(job, tenant, step: str) -> str:
	"""That step is done. Move to the one after it, or finish."""
	after = steps.ORDER.index(step) + 1
	if after >= len(steps.ORDER):
		job.db_set({"status": "Done", "step": None, "finished_at": now_datetime(), "error": None})
		return "Done"
	job.db_set(
		{
			"status": "Pending",
			"step": steps.ORDER[after],
			"attempts": 0,
			"error": None,
			"next_run_at": now_datetime(),
		}
	)
	if tenant.status == "Requested":
		tenant.db_set("status", "Provisioning")
	return "Pending"


def _later(job, why: str | None) -> str:
	"""Not finished. Come back, unless it has been long enough to be a person's."""
	attempts = (job.attempts or 0) + 1
	if attempts >= GIVE_UP_AFTER:
		return _stop(job, frappe.get_doc("Tenant", job.tenant), why or "stopped answering")
	job.db_set(
		{
			"status": "Waiting",
			"attempts": attempts,
			"error": why,
			"next_run_at": add_to_date(now_datetime(), seconds=_backoff(attempts)),
		}
	)
	return "Waiting"


def _stop(job, tenant, why: str) -> str:
	job.db_set({"status": "Failed", "error": why, "finished_at": now_datetime()})
	tenant.db_set("status", "Failed")
	return "Failed"


def _backoff(attempt: int) -> int:
	return BACKOFF[min(attempt, len(BACKOFF)) - 1]


def start(tenant: str) -> str:
	"""Queue a provision for a tenant, once.

	An open job is returned rather than a second one made: two jobs walking the
	same tenant is two sites.
	"""
	site.require_admin()
	open_already = frappe.get_all(
		"Provisioning Job",
		filters={"tenant": tenant, "kind": "Provision", "status": ["in", ("Pending", "Waiting")]},
		limit=1,
		pluck="name",
	)
	if open_already:
		return open_already[0]
	job = frappe.get_doc(
		{
			"doctype": "Provisioning Job",
			"tenant": tenant,
			"kind": "Provision",
			"status": "Pending",
			"step": steps.ORDER[0],
			"next_run_at": now_datetime(),
		}
	).insert(ignore_permissions=True)
	return job.name
