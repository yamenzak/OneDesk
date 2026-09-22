"""What a person may do to a workspace by hand, and how.

Every one of these exists because the alternative was editing a field. A Status
that an operator can set from a dropdown is a workspace dropped with no job, no
call to press and no R2 sweep behind it — a record saying the files are gone
while the files are still there. So the record is read-only and the verbs live
here.

**Each verb does exactly what the nightly ladder does.** `suspend` is not a
shortcut past `lifecycle`; it is `lifecycle.fall` with the rung named, which
queues the same job, runs the same steps and writes the same event. An operator
acting early and a clock acting on time are the same code, which is the only way
the second one stays tested.

**Two gates, as everywhere else in this module.** `require_admin` refuses on a
workspace site, and `only_for` refuses anybody without the operator role. The
first cannot be edited from a desk; the second is what keeps a curious
colleague out.
"""

import frappe

from onedesk.one_admin import ladder, lifecycle, runner, site

#: The rung an operator may send a workspace to, and what to warn them about
#: first. The client shows the warning; this list is what makes it possible to
#: get it wrong in only one place.
BY_HAND = {
	"Overdue": "",
	"Suspended": "The site stops serving. Nobody can log in until it is restored.",
	"Archived": "Press destroys the site, keeping its own backup. Restoring it afterwards is not automatic.",
	"Dropped": "Every file this workspace stored is deleted. Nothing comes back.",
}


def _may() -> None:
	site.require_admin()
	frappe.only_for(site.OPERATOR)


@frappe.whitelist()
def standing(tenant: str) -> dict:
	"""Where this workspace is, and what may be done to it from here.

	The form asks this rather than working it out in JavaScript, so the rungs a
	button offers and the rungs the ladder will walk cannot drift apart.
	"""
	_may()
	held = frappe.get_doc("Tenant", tenant)
	where = lifecycle.standing(held)
	below = ladder.below(held.status)
	where["next"] = below if below in BY_HAND else None
	where["warning"] = BY_HAND.get(below or "", "")
	where["may_restore"] = held.status in ("Overdue", "Suspended")
	return where


@frappe.whitelist()
def fall(tenant: str, rung: str) -> dict:
	"""Send a workspace down one rung, now rather than when the clock says.

	Refuses a rung that is not the next one. Skipping is how a workspace ends up
	archived without ever having been suspended, which means nobody was warned
	and no site was ever deactivated.
	"""
	_may()
	if rung not in BY_HAND:
		frappe.throw(frappe._("{0} is not a rung an operator sets.").format(rung))
	held = frappe.get_doc("Tenant", tenant)
	lifecycle.fall(held, rung)
	return standing(tenant)


@frappe.whitelist()
def restore(tenant: str) -> dict:
	"""Put it back to Live.

	The same call the payment webhook makes, and it refuses an archived
	workspace for the same reason: the site was destroyed, and rebuilding it
	from a backup is somebody's decision rather than a button's.
	"""
	_may()
	lifecycle.paid(frappe.get_doc("Tenant", tenant))
	return standing(tenant)


@frappe.whitelist()
def measure(tenant: str) -> dict:
	"""Count what this workspace is storing, now rather than tonight.

	The nightly sweep is the usual answer. This is for the conversation where
	somebody is asking why their bill says what it says.
	"""
	_may()
	from onedesk.one_admin import storage

	total = storage.measure(tenant)
	return {"storage_bytes": total}


@frappe.whitelist()
def refresh_domains(tenant: str) -> list:
	"""Ask press where each of this workspace's domains got to."""
	_may()
	from onedesk.one_admin import domains

	return domains.refresh(frappe.get_doc("Tenant", tenant))


@frappe.whitelist()
def resume(job: str) -> str:
	"""Give a failed job another go, from the step it stopped on.

	Not a restart. The step is a field and every step is safe to run twice, so
	resuming picks up where it stopped rather than provisioning a second site.
	"""
	_may()
	held = frappe.get_doc("Provisioning Job", job)
	if held.status != "Failed":
		frappe.throw(frappe._("{0} has not failed.").format(job))
	held.db_set(
		{
			"status": "Pending",
			"attempts": 0,
			"error": None,
			"next_run_at": frappe.utils.now_datetime(),
		}
	)
	return runner.advance(job)


@frappe.whitelist()
def walk(job: str) -> dict:
	"""Where a job has got to, as a list somebody can read.

	The step is a function name on the record, which tells a reader nothing. The
	walk comes from `steps.WALKS` rather than from anything stored, so a job
	opened after its kind gained a step shows the walk as it is now — which is
	the honest answer, because that is the walk it will finish on.
	"""
	_may()
	from onedesk.one_admin import steps

	held = frappe.db.get_value(
		"Provisioning Job", job, ["kind", "step", "status", "attempts", "error"], as_dict=True
	)
	if not held:
		frappe.throw(frappe._("{0} is not a job.").format(job))

	order = steps.WALKS.get(held.kind or "Provision") or ()
	at = order.index(held.step) if held.step in order else (len(order) if held.status == "Done" else 0)
	return {
		"kind": held.kind,
		"status": held.status,
		"attempts": held.attempts,
		"error": held.error,
		"at": at,
		"of": len(order),
		"steps": [
			{"name": name, "said": frappe._(steps.SAID.get(name, name)), "done": i < at}
			for i, name in enumerate(order)
		],
	}
