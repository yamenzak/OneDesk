"""What a workspace has to spend, and the only place that knows where it comes from.

**The balance is a sum, never a stored number.** There is no `credits_left`
field anywhere, on purpose: a stored balance can disagree with its own history,
and when it does there is no way to tell which of the two is lying. Summing the
rows costs one query and cannot drift.

**Reserve, then commit.** Reading a balance and then spending against it is a
race — two calls arriving together both see five credits and both spend four.
So a hold is taken under a lock on the workspace's own row before anybody talks
to a provider, and settled for what the call actually cost afterwards. The hold
is a *ceiling* priced from an action's declared limits, not a forecast; the
point is only that two calls cannot both spend the last credit.

**A spend names the grant it came out of.** Which is what makes the ledger
append-only: drawing down a bucket without rewriting it means writing a row that
points at it. `credits.py` decides which bucket and in what order, and has no
frappe in it.

This module is the only thing in the app that knows a balance is made of rows.
Everything above it asks for a number.
"""

from datetime import date

import frappe

from onedesk.one_admin import credits, site


class NotEnough(frappe.ValidationError):
	"""The workspace cannot afford this call. Said before one is made."""


#: A hold whose call never came back. A worker that died mid-flight would
#: otherwise eat a customer's credits for good, so they are let go nightly —
#: generously, because releasing one that is still running would let a second
#: call spend the same credits.
STALE_MINUTES = 60


def standing(tenant: str) -> dict:
	"""Everything a screen or a caller wants to know, in one query each."""
	site.require_admin()
	on = _today()
	buckets = _buckets(tenant)
	over = _overdrawn(tenant)
	holding = held(tenant)
	whole = credits.balance(buckets, on, over)
	live = credits.live(buckets, on)
	return {
		"balance": whole,
		"held": holding,
		"available": round(whole - holding, credits.PLACES),
		"expires_on": str(live[0].expires_on) if live and live[0].expires_on else None,
		"expiring": live[0].left if live and live[0].expires_on else 0,
	}


def balance(tenant: str) -> float:
	site.require_admin()
	return credits.balance(_buckets(tenant), _today(), _overdrawn(tenant))


def held(tenant: str, locking: bool = False) -> float:
	"""Credits promised to calls already in flight."""
	return _summed(
		"""
		SELECT COALESCE(SUM(credits), 0)
		  FROM `tabCredit Reservation`
		 WHERE tenant = %s AND state = 'Held'
		""",
		tenant,
		locking,
	)


def grant(
	tenant: str,
	amount: float,
	source: str,
	reference: str | None = None,
	expires_on: date | str | None = None,
	key: str | None = None,
	why: str | None = None,
) -> str:
	"""Credit added, by a payment or by an operator.

	`key` is the idempotency: it is unique on the row, so a webhook delivered
	twice meets a database index rather than a check somebody remembered to
	write. The second delivery gets the first delivery's entry back.
	"""
	site.require_admin()
	amount = _amount(amount)
	if key:
		already = frappe.db.get_value("Credit Ledger Entry", {"key": key}, "name")
		if already:
			return already

	entry = frappe.get_doc(
		{
			"doctype": "Credit Ledger Entry",
			"tenant": tenant,
			"kind": "Grant",
			"credits": amount,
			"expires_on": expires_on,
			"source": source,
			"reference": reference,
			"key": key,
			"why": why,
		}
	)
	entry.flags.ignore_permissions = True
	entry.insert()
	entry.submit()
	return entry.name


def reserve(tenant: str, amount: float, why: str | None = None, reference: str | None = None) -> str:
	"""Hold credits for a call that is about to be made, or refuse it.

	This is the only place a call is ever refused for money, and it runs before
	the provider is touched. Refusing after would mean a call we paid for and
	told the customer they could not have.
	"""
	site.require_admin()
	amount = _amount(amount)
	_lock(tenant)

	if not credits.enough(
		_buckets(tenant, locking=True), amount, held(tenant, locking=True), _today()
	):
		frappe.throw(
			frappe._("{0} does not have {1} credits to spend.").format(tenant, amount),
			NotEnough,
		)

	holding = frappe.get_doc(
		{
			"doctype": "Credit Reservation",
			"tenant": tenant,
			"state": "Held",
			"credits": amount,
			"why": why,
			"reference": reference,
		}
	)
	holding.flags.ignore_permissions = True
	holding.insert()
	return holding.name


def commit(reservation: str, amount: float) -> list[str]:
	"""Charge what the call actually cost and let the rest of the hold go.

	The actual may come to more than the hold, and when it does it is charged
	anyway: the provider answered, the cost is real, and a balance that goes
	negative is a fact about this workspace rather than an error. What must not
	happen is charging an estimate, which is why this takes a number somebody
	else metered rather than working one out.
	"""
	site.require_admin()
	holding = frappe.get_doc("Credit Reservation", reservation)
	if holding.state != "Held":
		frappe.throw(frappe._("{0} was already {1}.").format(reservation, holding.state.lower()))

	amount = round(float(amount or 0), credits.PLACES)
	_lock(holding.tenant)
	if amount <= 0:
		_settle(holding, 0)
		return []

	written = []
	for one in credits.draw(_buckets(holding.tenant, locking=True), amount, _today()):
		entry = frappe.get_doc(
			{
				"doctype": "Credit Ledger Entry",
				"tenant": holding.tenant,
				"kind": "Spend",
				"credits": -one.credits,
				"against": one.bucket,
				"source": "Run",
				"reference": holding.reference,
				"why": holding.why,
			}
		)
		entry.flags.ignore_permissions = True
		entry.insert()
		entry.submit()
		written.append(entry.name)

	_settle(holding, amount)
	return written


def release(reservation: str) -> None:
	"""A call that never happened. The hold goes and nothing is charged."""
	site.require_admin()
	holding = frappe.get_doc("Credit Reservation", reservation)
	if holding.state != "Held":
		return
	holding.db_set({"state": "Released", "settled": 0}, update_modified=False)


def nightly() -> None:
	"""Let go of holds whose call never came back.

	A worker that died mid-flight leaves credits promised to nothing, and
	nothing else would ever release them.
	"""
	stale = frappe.utils.add_to_date(frappe.utils.now_datetime(), minutes=-STALE_MINUTES)
	for row in frappe.get_all(
		"Credit Reservation", filters={"state": "Held", "creation": ["<", stale]}, pluck="name"
	):
		release(row)


# ------------------------------------------------------------------ the rows


def _buckets(tenant: str, locking: bool = False) -> list[credits.Bucket]:
	"""Every grant and what is left in it.

	What is left is the grant plus everything drawn from it, because a spend is
	negative and a refund is positive. One query, and no number anybody stored.
	"""
	rows = frappe.db.sql(
		"""
		SELECT g.name, g.expires_on,
		       g.credits + COALESCE(SUM(d.credits), 0) AS remaining
		  FROM `tabCredit Ledger Entry` g
		  LEFT JOIN `tabCredit Ledger Entry` d
		         ON d.against = g.name AND d.docstatus = 1
		 WHERE g.tenant = %s AND g.kind = 'Grant' AND g.docstatus = 1
		 GROUP BY g.name, g.expires_on, g.credits
		"""
		+ (" FOR UPDATE" if locking else ""),
		(tenant,),
		as_dict=True,
	)
	return [
		credits.Bucket(name=row.name, left=float(row.remaining or 0), expires_on=row.expires_on)
		for row in rows
	]


def _overdrawn(tenant: str, locking: bool = False) -> float:
	"""Spends that belong to no grant, which is money owed rather than credit.

	Counted always, and never expired: a bucket's date says when unspent credit
	stops being worth anything, and an overdraw was never in a bucket.
	"""
	return _summed(
		"""
		SELECT COALESCE(SUM(credits), 0)
		  FROM `tabCredit Ledger Entry`
		 WHERE tenant = %s AND kind != 'Grant' AND docstatus = 1
		   AND (against IS NULL OR against = '')
		""",
		tenant,
		locking,
	)


def _summed(query: str, tenant: str, locking: bool = False) -> float:
	"""One number off one query.

	Raw SQL because these are sums, and a sum is the one thing frappe's query
	API makes longer to write than to read.
	"""
	rows = frappe.db.sql(query + (" FOR UPDATE" if locking else ""), (tenant,))
	return round(float(rows[0][0] or 0) if rows else 0.0, credits.PLACES)


def _settle(holding, amount: float) -> None:
	holding.db_set({"state": "Settled", "settled": amount}, update_modified=False)


def _lock(tenant: str) -> None:
	"""Serialise every credit operation for one workspace.

	The workspace's own row is the mutex: it is the one row every one of these
	touches and nothing else contends for it.

	**The lock alone is not enough, and this was measured rather than reasoned.**
	Two processes reserving seven credits against a balance of ten both
	succeeded: the second waited for the first exactly as intended, and then
	read a balance from the snapshot its transaction had taken *before* the
	first one committed. InnoDB's repeatable read fixes that snapshot at a
	transaction's first read, and a plain SELECT afterwards never sees past it.

	So every read this decision rests on is a locking read — `FOR UPDATE`, which
	reads the latest committed row rather than the snapshot — and the mutex is
	what stops the two of them interleaving between the read and the insert.
	"""
	if not frappe.db.get_value("Tenant", tenant, "name", for_update=True):
		frappe.throw(frappe._("{0} is not a workspace.").format(tenant))


def _amount(amount: float) -> float:
	amount = round(float(amount or 0), credits.PLACES)
	if amount <= 0:
		frappe.throw(frappe._("Credits have to be more than nothing."))
	return amount


def _today() -> date:
	return frappe.utils.getdate()


#: What usage may be grouped by, as the reservation's own columns.
USAGE_BY = ("tenant", "why")


def usage(start, end, by: list[str], tenant: str | None = None, model: str | None = None) -> list:
	"""Model calls between two dates, grouped, for the operator's usage report.

	One reservation is one call: `settled` is what it was charged once the
	provider said what it used, and `why` names the model. A held reservation is
	a call still running and a released one never happened, so neither is usage.
	"""
	site.require_admin()
	# No grouping is the whole period as one row, which is what a total is.
	by = [key for key in by if key in USAGE_BY]
	where = ["state = 'Settled'", "creation >= %(start)s", "creation < %(end)s"]
	if tenant:
		where.append("tenant = %(tenant)s")
	if model:
		where.append("why = %(model)s")
	grouped = ", ".join(by)
	return frappe.db.sql(
		f"""
		SELECT {grouped + "," if by else ""}
		       COUNT(DISTINCT why) AS models,
		       COUNT(DISTINCT tenant) AS workspaces,
		       COUNT(*) AS calls,
		       SUM(settled) AS credits,
		       MAX(creation) AS last
		  FROM `tabCredit Reservation`
		 WHERE {" AND ".join(where)}
		 {"GROUP BY " + grouped if by else ""}
		 ORDER BY credits DESC
		""",
		{"start": start, "end": end, "tenant": tenant, "model": model},
		as_dict=True,
	)
