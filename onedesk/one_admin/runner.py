"""Driving a Provisioning Job forward, on a cron rather than in a request.

A job resumes and never repeats; waiting is not failing; backoff is per step
and grows, to a cap.
"""

import json
from time import monotonic

import frappe
from frappe.utils import add_to_date, get_datetime, now_datetime

from onedesk.one_admin import faults, ladder, site, steps

BACKOFF = (10, 30, 60, 120, 300)

GIVE_UP_AFTER = 12

AT_A_TIME = 5

A_JOB_SECONDS = 45

A_TICK_SECONDS = 180


def tick() -> None:
	"""The cron entry. Never raises: one bad job must not stop the queue.

	Each step is committed on its own, so one that throws loses only itself,
	and a throw is an attempt like any other (_counted). A job left over when
	the tick's time is up is first in the next tick, being the most overdue.
	"""
	if not site.is_admin():
		return
	ends = monotonic() + A_TICK_SECONDS
	for name in _due():
		if monotonic() >= ends:
			return
		try:
			_drive(name)
		except Exception as raised:
			_counted(name, raised)
		frappe.db.commit()


def run(name: str) -> None:
	"""A background job driving one job at once, without waiting for the tick."""
	try:
		_drive(name)
	except Exception as raised:
		_counted(name, raised)
	frappe.db.commit()


def _drive(name: str) -> None:
	"""Step after step while each finishes at once, committing each: it stops
	at a wait or a backoff, and after `A_JOB_SECONDS` so one job does not hold
	the worker; what is left is due and the next tick carries on."""
	frappe.db.commit()
	ends = monotonic() + A_JOB_SECONDS
	while _take(name) and advance(name) == "Pending":
		frappe.db.commit()
		if monotonic() >= ends:
			return


def _take(name: str) -> bool:
	"""Whether this job is due, holding its row until the step is committed.

	The webhook's run and the tick can reach one job together. The row lock
	is skipped rather than waited on, so the second finds nothing to do."""
	held = frappe.db.get_value(
		"Provisioning Job", name, ["status", "next_run_at"], as_dict=True, for_update=True, skip_locked=True
	)
	return bool(held and held.status in ("Pending", "Waiting") and get_datetime(held.next_run_at) <= now_datetime())


def _counted(name: str, raised: Exception) -> None:
	"""A step that threw what no step should: undone, logged, and counted, so
	it backs off and in the end stops rather than running every tick for ever."""
	frappe.db.rollback()
	frappe.log_error(title=f"Provisioning {name}")
	try:
		_later(frappe.get_doc("Provisioning Job", name), str(raised)[: faults.KEPT])
	except Exception:
		frappe.db.rollback()
		frappe.log_error(title=f"Provisioning {name}, counting the attempt")


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

	walk = _walk(job)
	step = job.step or walk[0]
	tenant = frappe.get_doc("Tenant", job.tenant)
	if job.kind in (None, "", "Provision"):
		if tenant.status not in ladder.BUILDING:
			return _called_off(job, f"{tenant.name} is {tenant.status}, so it is not built again")
		if tenant.status == "Failed":
			tenant.db_set("status", "Provisioning", notify=True)

	try:
		waiting = getattr(steps, step)(job, tenant) == steps.WAIT
	except steps.CalledOff as off:
		return _called_off(job, str(off))
	except faults.Busy:
		return _waiting(job)
	except faults.Refused as refused:
		if isinstance(refused, faults.Again):
			return _later(job, str(refused))
		return _stop(job, tenant, str(refused))

	if waiting:
		return _waiting(job)
	return _next(job, tenant, step, walk)


def _walk(job) -> tuple:
	"""The steps this kind of job takes.

	Defaults to provisioning, because a job written before there were other
	kinds carries no kind and was one.
	"""
	walk = steps.WALKS.get(job.kind or "Provision")
	if not walk:
		raise faults.Refused(f"there is no such job as a {job.kind}")
	return walk


def _next(job, tenant, step: str, walk: tuple) -> str:
	"""That step is done. Move to the one after it, or finish."""
	after = walk.index(step) + 1
	if after >= len(walk):
		job.db_set(
			{"status": "Done", "step": None, "finished_at": now_datetime(), "error": None}, notify=True
		)
		return "Done"
	job.db_set(
		{
			"status": "Pending",
			"step": walk[after],
			"attempts": 0,
			"error": None,
			"next_run_at": now_datetime(),
		},
		notify=True,
	)
	if job.kind in (None, "", "Provision") and tenant.status == "Requested":
		tenant.db_set("status", "Provisioning", notify=True)
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
		},
		notify=True,
	)
	return "Waiting"


def _called_off(job, why: str) -> str:
	"""Nothing left to do: the workspace is no longer going where the job was
	taking it (steps.CalledOff). Done, saying why on the step it stopped at,
	and nobody is told, because nothing failed."""
	job.db_set({"status": "Done", "finished_at": now_datetime(), "error": why}, notify=True)
	return "Done"


WAIT_SECONDS = 60


def _waiting(job) -> str:
	"""Press is still at it. Ask again in a minute, and do not count it.

	Waiting was counted as a failed attempt, which gave a build about forty
	minutes before it was marked Failed and the customer mailed Delayed,
	though press might finish at forty-five. A job that waits for hours is on
	Home instead (home._slow_builds), where a person can look.
	"""
	job.db_set(
		{
			"status": "Waiting",
			"error": None,
			"next_run_at": add_to_date(now_datetime(), seconds=WAIT_SECONDS),
		},
		notify=True,
	)
	return "Waiting"


def _stop(job, tenant, why: str) -> str:
	"""The job is somebody's problem now.

	Only a failed provision marks the workspace Failed. A failed archive or a
	failed suspension must leave the workspace where it was: it is still live,
	still serving, and turning it into a broken record would hide a working
	workspace from every screen that filters on status — and, worse, take it off
	the ladder so nothing ever tries again.
	"""
	job.db_set({"status": "Failed", "error": why, "finished_at": now_datetime()}, notify=True)
	if job.kind in (None, "", "Provision"):
		tenant.db_set("status", "Failed", notify=True)
	from onedesk.one_admin import tell

	tell.job_failed(job)
	return "Failed"


def _backoff(attempt: int) -> int:
	return BACKOFF[min(attempt, len(BACKOFF)) - 1]


def start(tenant: str, kind: str = "Provision", payload: dict | None = None) -> str:
	"""Queue a job for a tenant, once.

	An open job of the same kind is returned rather than a second one made: two
	jobs walking the same tenant is two sites, and two archives is two attempts
	to destroy the same one.
	"""
	site.require_admin()
	from onedesk.one_admin import testbed

	testbed.refuse(tenant, "moved")
	said = json.dumps(payload, sort_keys=True) if payload else None
	open_already = frappe.get_all(
		"Provisioning Job",
		filters={"tenant": tenant, "kind": kind, "status": ["in", ("Pending", "Waiting")], **({"payload": said} if said else {})},
		limit=1,
		pluck="name",
	)
	if open_already:
		return open_already[0]
	job = frappe.get_doc(
		{
			"doctype": "Provisioning Job",
			"tenant": tenant,
			"kind": kind,
			"status": "Pending",
			"step": steps.WALKS[kind][0],
			"next_run_at": now_datetime(),
			"payload": said,
		}
	).insert(ignore_permissions=True)
	return job.name


def start_now(tenant: str) -> str:
	"""A paid signup's job, begun as soon as the payment is committed. The
	page promises the workspace is being built, and the tick is minutes off."""
	job = start(tenant)
	frappe.enqueue(
		"onedesk.one_admin.runner.run",
		name=job,
		job_id=f"one_admin_job_{job}",
		deduplicate=True,
		enqueue_after_commit=True,
	)
	return job
