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

#: The doctype a head or a suggestion registers against, named here so the
#: ledger stays the only module that spells it (tests/test_ledger.py).
ENTRY = "Credit Ledger Entry"


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


def reserve(
	tenant: str, amount: float, why: str | None = None, reference: str | None = None, action: str | None = None
) -> str:
	"""Hold credits for a call that is about to be made, or refuse it.

	This is the only place a call is ever refused for money, and it runs before
	the provider is touched. Refusing after would mean a call we paid for and
	told the customer they could not have.
	"""
	site.require_admin()
	amount = _amount(amount)
	_lock(tenant)

	# Our own workspace (house.py) is never refused: its calls are our cost,
	# and what it spends is written down all the same.
	ours = frappe.db.get_value("Tenant", tenant, "is_house")
	if not ours and not credits.enough(
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
			"action": action,
		}
	)
	holding.flags.ignore_permissions = True
	holding.insert()
	return holding.name


def commit(reservation: str, amount: float, usd: float | None = None) -> list[str]:
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
		_settle(holding, 0, usd)
		return []

	written = []
	# A call's `why` is the model it ran on (gateway.call), named as one.
	model = holding.why if holding.why and frappe.db.exists("AI Model", holding.why) else None
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
				"model": model,
			}
		)
		entry.flags.ignore_permissions = True
		entry.insert()
		entry.submit()
		written.append(entry.name)

	if frappe.session.user == "Guest" and written:
		# The call came through the proxy, signed by the workspace rather than
		# signed in, and a spend "created by Guest" reads as nobody's.
		frappe.db.set_value(
			"Credit Ledger Entry",
			{"name": ["in", written]},
			{"owner": "Administrator", "modified_by": "Administrator"},
			update_modified=False,
		)
	_settle(holding, amount, usd)
	return written


def left_of(grant: str) -> float:
	"""What is left of one grant: it, plus everything drawn from it."""
	rows = frappe.db.sql(
		"""
		SELECT g.credits + COALESCE(SUM(d.credits), 0)
		  FROM `tabCredit Ledger Entry` g
		  LEFT JOIN `tabCredit Ledger Entry` d ON d.against = g.name AND d.docstatus = 1
		 WHERE g.name = %s
		 GROUP BY g.name, g.credits
		""",
		(grant,),
	)
	return round(float(rows[0][0] or 0) if rows else 0.0, credits.PLACES)


def taken_back(grant: str) -> float:
	"""How much of a grant an operator took back (take_back)."""
	rows = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(credits), 0) FROM `tabCredit Ledger Entry`
		 WHERE against = %s AND kind = 'Spend' AND source = 'Operator' AND docstatus = 1
		""",
		(grant,),
	)
	return round(-float(rows[0][0] or 0), credits.PLACES)


def grants(tenant: str, limit: int = 12) -> list[dict]:
	"""A workspace's latest grants, each with what is left of it."""
	rows = frappe.get_all(
		"Credit Ledger Entry",
		filters={"tenant": tenant, "kind": "Grant", "docstatus": 1},
		fields=["name", "credits", "source", "why", "expires_on", "creation"],
		order_by="creation desc",
		limit=limit,
	)
	return [{**one, "left": left_of(one.name)} for one in rows]


def taken(tenant: str, limit: int = 5) -> list[dict]:
	"""The credits operators took back from a workspace (take_back)."""
	return frappe.get_all(
		"Credit Ledger Entry",
		filters={"tenant": tenant, "kind": "Spend", "source": "Operator", "docstatus": 1},
		fields=["credits", "against", "reference", "why", "creation"],
		order_by="creation desc",
		limit=limit,
	)


def said_of(grant: str) -> dict:
	"""What a grant was for, for a spend drawn from it to name."""
	return frappe.db.get_value("Credit Ledger Entry", grant, ["why", "source"], as_dict=True) or {}


def mend_costs() -> None:
	"""What the provider charged us for calls settled before that was kept:
	the credits charged over the markup and the credits a dollar buys, which
	is how they were priced (pricing.bill). Close, not exact, for a call that
	was charged its hold."""
	settings = frappe.get_single("One Admin Settings")
	per_dollar = float(settings.credits_per_dollar or 0)
	if not per_dollar:
		return
	default = float(settings.default_markup or 0) or 1
	frappe.db.sql(
		"""
		UPDATE `tabCredit Reservation` r
		  LEFT JOIN `tabAI Model` m ON m.name = r.why
		   SET r.usd = r.settled / (%(per_dollar)s * COALESCE(NULLIF(m.markup, 0), %(default)s))
		 WHERE r.state = 'Settled' AND (r.usd IS NULL OR r.usd = 0) AND r.settled > 0
		""",
		{"per_dollar": per_dollar, "default": default},
	)


def mend() -> None:
	"""A spend's model as a link to it, and the spends a workspace's calls
	wrote as nobody (Guest), for rows written before commit said either
	(patches/credit_model.py)."""
	frappe.db.sql(
		"""
		UPDATE `tabCredit Ledger Entry` e
		  JOIN `tabAI Model` m ON m.name = e.why
		   SET e.model = e.why
		 WHERE e.source = 'Run' AND (e.model IS NULL OR e.model = '')
		"""
	)
	frappe.db.sql(
		"""
		UPDATE `tabCredit Ledger Entry`
		   SET owner = 'Administrator', modified_by = 'Administrator'
		 WHERE owner = 'Guest'
		"""
	)


def take_back(grant: str, why: str) -> dict:
	"""What is left of a grant an operator gave, taken back.

	A spend of the rest of it against it, rather than cancelling the grant:
	what was already spent from it stays spent, and the ledger stays a list of
	things that happened. Only an operator's grant: a plan's or a pack's was
	paid for.
	"""
	site.require_admin()
	held = frappe.get_doc("Credit Ledger Entry", grant)
	if held.kind != "Grant" or held.source != "Operator" or held.docstatus != 1:
		frappe.throw(frappe._("Only credits an operator gave can be taken back."))
	if not (why or "").strip():
		frappe.throw(frappe._("Say why they are taken back."))
	_lock(held.tenant)
	left = left_of(grant)
	if left <= 0:
		return {"entry": None, "tenant": held.tenant}
	entry = frappe.get_doc(
		{
			"doctype": "Credit Ledger Entry",
			"tenant": held.tenant,
			"kind": "Spend",
			"credits": -left,
			"against": grant,
			"source": "Operator",
			"reference": frappe.session.user,
			"why": why,
		}
	)
	entry.flags.ignore_permissions = True
	entry.insert()
	entry.submit()
	return {"entry": entry.name, "tenant": held.tenant}


def last_gift(tenant: str) -> dict | None:
	"""The last credits an operator gave, and their note, for the workspace's
	administrators to be told of (proxy.hello)."""
	held = frappe.get_all(
		"Credit Ledger Entry",
		filters={"tenant": tenant, "kind": "Grant", "source": "Operator", "docstatus": 1},
		fields=["name", "credits", "why", "expires_on"],
		order_by="creation desc",
		limit=1,
	)
	if not held or taken_back(held[0].name):
		# Taken back before the workspace heard of it: nothing to tell.
		return None
	one = held[0]
	return {
		"entry": one.name,
		"credits": one.credits,
		"why": one.why,
		"expires_on": str(one.expires_on) if one.expires_on else None,
	}


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


def _settle(holding, amount: float, usd: float | None = None) -> None:
	"""Settled at what was charged, and what the provider charged us for it,
	which is what AI Usage sets the charge against."""
	holding.db_set({"state": "Settled", "settled": amount, "usd": usd or 0}, update_modified=False)


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
USAGE_BY = ("tenant", "why", "reference", "action")


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
		       SUM(usd) AS usd,
		       MAX(creation) AS last
		  FROM `tabCredit Reservation`
		 WHERE {" AND ".join(where)}
		 {"GROUP BY " + grouped if by else ""}
		 ORDER BY credits DESC
		""",
		{"start": start, "end": end, "tenant": tenant, "model": model},
		as_dict=True,
	)


def arrived(tenant: str, start, end) -> list:
	"""What came into one workspace between two dates: every grant and refund,
	one row each, for its own ledger. What went out is `daily`, because a spend
	is a row per call and per bucket, which is the right record and the wrong
	thing to read."""
	site.require_admin()
	return frappe.get_all(
		"Credit Ledger Entry",
		filters={
			"tenant": tenant,
			"kind": ["in", ("Grant", "Refund")],
			"docstatus": 1,
			"creation": ["between", (start, end)],
		},
		fields=["creation", "kind", "source", "credits", "expires_on", "why"],
		order_by="creation desc",
	)


def daily(tenant: str, start, end) -> list:
	"""What one workspace spent each day between two dates, for its own chart.

	Only days with a call are returned; the chart fills the gaps, because a day
	nobody asked anything is a zero the caller can draw and not a row worth
	storing.
	"""
	site.require_admin()
	return frappe.db.sql(
		"""
		SELECT DATE(creation) AS day, COUNT(*) AS calls, SUM(settled) AS credits
		  FROM `tabCredit Reservation`
		 WHERE state = 'Settled' AND tenant = %(tenant)s
		   AND creation >= %(start)s AND creation < %(end)s
		 GROUP BY DATE(creation)
		 ORDER BY day
		""",
		{"tenant": tenant, "start": start, "end": end},
		as_dict=True,
	)
