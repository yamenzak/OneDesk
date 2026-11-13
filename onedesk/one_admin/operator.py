"""What a person may do to a workspace by hand, and how.

The record is read-only and the verbs live here; each does exactly what the
nightly ladder does, behind two gates (`require_admin`, `only_for`).
"""

import frappe

from onedesk.one_admin import ladder, lifecycle, runner, site

BY_HAND = {
	"Overdue": "",
	"Suspended": "The site stops. No one can sign in until it's restored.",
	"Archived": "The site is deleted after its backup and files are kept. It can be rebuilt from them.",
	"Dropped": "Every file this workspace stored is deleted permanently.",
}

CALLED = {
	"Overdue": "Mark Overdue",
	"Suspended": "Suspend",
	"Archived": "Archive",
	"Dropped": "Delete Files",
}


def _may() -> None:
	site.require_admin()
	frappe.only_for(site.OPERATOR)


@frappe.whitelist(methods=["POST"])
def order_server(tenant: str | None = None) -> dict:
	"""The next server, or one for a workspace that has its own, ordered in
	the background: about 25 minutes, and it joins Settings by itself."""
	_may()
	from onedesk.one_admin import servers

	servers.begin(tenant)
	return {"ordered": True}


@frappe.whitelist(methods=["POST"])
def connect_server() -> dict:
	"""A machine that is not on AWS joins as a server: the line to run on it."""
	_may()
	from onedesk.one_admin import servers

	return servers.connect()


@frappe.whitelist(methods=["POST"])
def connect_again(server: str) -> dict:
	"""A released machine joins again under its own name: the line to run on it."""
	_may()
	from onedesk.one_admin import servers

	return servers.connect(server)


@frappe.whitelist(methods=["POST"])
def release_server(server: str) -> dict:
	"""A connected machine let go: its sessions end, and the line that
	removes what Connect Server put on it."""
	_may()
	from onedesk.one_admin import releasing

	return releasing.begin(server)


@frappe.whitelist(methods=["POST"])
def finish_release(server: str) -> dict:
	"""The operator says the release line ran, when the machine could not."""
	_may()
	from onedesk.one_admin import releasing

	return {"done": releasing.finish(server)}


@frappe.whitelist()
def standing(tenant: str) -> dict:
	"""Where this workspace is, and what may be done to it from here.

	The form asks this rather than working it out in JavaScript, so the rungs a
	button offers and the rungs the ladder will walk cannot drift apart.
	"""
	_may()
	held = frappe.get_doc("Tenant", tenant)
	where = lifecycle.standing(held)
	below = ladder.by_hand(held.status)
	where["next"] = below if below in BY_HAND else None
	where["warning"] = BY_HAND.get(below or "", "")
	where["verb"] = frappe._(CALLED[below]) if below in CALLED else None
	where["may_restore"] = held.status in ("Overdue", "Suspended") and not held.is_test
	if held.is_test:
		where.update({"next": None, "warning": "", "verb": None})
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
		frappe.throw(frappe._("Operators can't set {0}.").format(rung))
	held = frappe.get_doc("Tenant", tenant)
	from onedesk.one_admin import log

	lifecycle.fall(held, rung, log.said("by_hand"))
	return standing(tenant)


@frappe.whitelist()
def backups(tenant: str) -> list[dict]:
	"""Every backup kept of a workspace in the locked bucket, newest first."""
	_may()
	from onedesk.one_admin import backups as kept

	return kept.listed(frappe.db.get_value("Tenant", tenant, "slug") or tenant)


@frappe.whitelist(methods=["POST"])
def rebuild(tenant: str, day: str, where: str = "daily") -> str:
	"""An archived or dropped workspace built again from a kept backup, on a
	new site: the job that does it. Billing is set up again separately."""
	_may()
	status = frappe.db.get_value("Tenant", tenant, "status")
	if status not in ("Archived", "Dropped"):
		frappe.throw(frappe._("Only an archived workspace is rebuilt. Use Roll Back for one that is running."))
	return runner.start(tenant, "Rebuild", {"day": day, "where": where})


@frappe.whitelist(methods=["POST"])
def roll_back(tenant: str, day: str, where: str = "daily") -> str:
	"""A running workspace's site put back to a kept backup: the job."""
	_may()
	status = frappe.db.get_value("Tenant", tenant, "status")
	if status not in ("Live", "Overdue", "Suspended"):
		frappe.throw(frappe._("Only a running workspace is rolled back. Use Rebuild for an archived one."))
	return runner.start(tenant, "Roll Back", {"day": day, "where": where})


@frappe.whitelist(methods=["POST"])
def move(tenant: str, day: str, where: str = "daily") -> str:
	"""A live workspace built on another server from a kept backup: the job."""
	_may()
	if frappe.db.get_value("Tenant", tenant, "status") != "Live":
		frappe.throw(frappe._("Only a live workspace is moved."))
	return runner.start(tenant, "Move", {"day": day, "where": where})


@frappe.whitelist(methods=["POST"])
def update_now(tenant: str) -> dict:
	"""The workspace moves to its server's newest version now instead of at
	its window."""
	_may()
	from onedesk.one_admin import releases

	return releases.update_now(frappe.get_doc("Tenant", tenant))


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
	"""Ask Cloudflare where each of this workspace's domains has got to."""
	_may()
	from onedesk.one_admin import domains

	return domains.refresh(frappe.get_doc("Tenant", tenant))


@frappe.whitelist(methods=["POST"])
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
		},
		notify=True,
	)
	return runner.advance(job)


@frappe.whitelist(methods=["POST"])
def run_now(job: str) -> str:
	"""Run the next step of a job that is due and has not moved, now.

	For when the scheduler has stopped or a worker died holding it. The same
	`runner.advance` the tick calls, one step, and every step is safe to run
	twice, so pressing it on a job that was about to move does no harm.
	"""
	_may()
	status = frappe.db.get_value("Provisioning Job", job, "status")
	if status not in ("Pending", "Waiting"):
		frappe.throw(frappe._("{0} is not waiting to run.").format(job))
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
			{"name": name, "said": str(steps.SAID.get(name, name)), "done": i < at}
			for i, name in enumerate(order)
		],
	}


@frappe.whitelist(methods=["POST"])
def retry_signup(request: str) -> dict:
	"""Build the workspace a paid signup never got.

	The worst state in the system: money taken and nothing to show for it.
	`signup.accept` is the same call the Stripe webhook makes and is idempotent
	— a request that did create a workspace returns it rather than making a
	second one — so this is safe on a request whose status is wrong.
	"""
	_may()
	from onedesk.one_admin import signup

	asked = frappe.get_doc("Account Request", request)
	if asked.status not in ("Paid", "Failed"):
		frappe.throw(frappe._("{0} hasn't been paid.").format(request))
	if asked.tenant:
		frappe.throw(
			frappe._("{0} already has a workspace. Resume its job instead.").format(request)
		)
	return {"tenant": signup.accept(request)}


@frappe.whitelist()
def refresh_domain(domain: str) -> dict:
	"""Ask Cloudflare where this domain has got to, now.

	A domain waits until somebody points the DNS, and nothing tells us when
	they do; Cloudflare keeps checking, and this asks it what it found. The workspace has the same button; this is the one for
	whoever is on the phone to them.
	"""
	_may()
	from onedesk.one_admin import domains

	held = frappe.get_doc("Tenant Domain", domain)
	domains.refresh(frappe.get_doc("Tenant", held.tenant))
	return frappe.db.get_value("Tenant Domain", domain, ["status", "said"], as_dict=True) or {}


@frappe.whitelist()
def sold(offering: str) -> dict:
	"""Which workspaces have this: a plan's are those on it, an add-on's
	those carrying it. A credit pack is bought once and used up, so nobody
	"has" one: `kind` says so and the counts are nought.

	Shown before somebody edits one.
	"""
	_may()
	kind = frappe.db.get_value("Offering", offering, "kind")
	if kind == "Add-on":
		names = frappe.get_all(
			"Tenant Add-on", filters={"offering": offering, "parenttype": "Tenant"}, pluck="parent", distinct=True
		)
	elif kind == "Plan":
		names = frappe.get_all("Tenant", filters={"offering": offering}, pluck="name")
	else:
		names = []
	live = frappe.get_all("Tenant", filters={"name": ["in", names or [""]], "status": "Live"}, pluck="name")
	return {"kind": kind, "all": len(names), "live": len(live), "workspaces": names}


@frappe.whitelist()
def try_the_gateway(prompt: str) -> dict:
	"""One model call, so an operator can prove the gateway is configured.

	Un-metered and deliberately so: there is no ledger yet, and a settings screen
	that cannot be tested until the billing is built is a settings screen
	somebody fills in wrong and finds out from a customer.
	"""
	_may()
	from onedesk.one_admin import gateway
	from onedesk.one_ai import models

	model = models.pick("talk")[0]
	words, _wants, _body = gateway.talk(model, [gateway.said(prompt)], tags={"job": "test"})
	return {"model": model, "said": words}


@frappe.whitelist(methods=["POST"])
def give_credits(tenant: str, credits: float, why: str, expires_on: str | None = None) -> dict:
	"""Credit an operator adds by hand — goodwill, a correction, a trial.

	A grant rather than an adjustment to a balance, because there is no balance
	to adjust: it is a sum over rows, and this writes one of them.
	"""
	_may()
	from onedesk.one_admin import ledger

	entry = ledger.grant(
		tenant,
		float(credits),
		"Operator",
		reference=frappe.session.user,
		expires_on=expires_on or None,
		why=why,
	)
	return {"entry": entry, "standing": ledger.standing(tenant)}


@frappe.whitelist(methods=["POST"])
def take_back_credits(entry: str, why: str) -> dict:
	"""What is left of credits an operator gave, taken back (ledger.take_back)."""
	_may()
	from onedesk.one_admin import ledger

	taken = ledger.take_back(entry, why)
	return {"entry": taken["entry"], "standing": ledger.standing(taken["tenant"])}


@frappe.whitelist()
def credit_standing(tenant: str) -> dict:
	"""What a workspace has, and what it has spent on AI since the month began."""
	_may()
	from frappe.utils import add_days, get_first_day, getdate

	from onedesk.one_admin import ledger

	said = ledger.standing(tenant)
	month = ledger.usage(get_first_day(getdate()), add_days(getdate(), 1), [], tenant=tenant)
	said["month_calls"] = (month[0].calls if month else 0) or 0
	said["month_credits"] = round((month[0].credits if month else 0) or 0, 4)
	return said
