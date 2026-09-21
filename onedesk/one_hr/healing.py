"""What the system teaches itself, and the one rule that keeps it safe.

A router reboots, an office takes a second line for the 5GHz band, a warehouse
registered at its office door has everybody clocking in at the gate two hundred
metres away. Today each of those locks people out on a Monday morning and needs
somebody to edit a settings box. Here they become proposals.

**Only a clock-in that was already corroborated another way may teach anything.**
Three colleagues in a café cannot promote the café, because none of them was
inside a fence or on a known network when they voted. And **nothing heals
towards less security**: a proposal can widen *where* people may clock in, never
*who* may. Credentials, employees and standing are never promoted automatically.

Run nightly rather than on every clock-in. A proposal is a claim about a
pattern, and a pattern is not visible from inside one request.
"""

import frappe
from frappe.utils import add_to_date, now_datetime, nowdate

from onedesk.one_hr import policy, rules

#: How far back a night's pass looks. Long enough that a new address seen on
#: Friday and again on Monday is one pattern rather than two.
WINDOW_DAYS = 7

#: How close two positions have to be to count as the same place. Fifty metres
#: is a building rather than a street, and it is the radius a proposed zone
#: opens with.
CLUSTER_METRES = 50


def nightly() -> None:
	"""Everything that learns, once a day."""
	standings()
	if policy.on("one_learn_networks"):
		networks()
	if policy.on("one_learn_zones"):
		zones()
	forget_photos()


def standings() -> None:
	"""Each employee's standing, from their last ninety days of attempts.

	Never used to refuse anybody. It decides whose observations count when the
	system teaches itself something new: three clean months makes somebody a
	witness, a first week does not.
	"""
	if not frappe.db.has_column("Employee", "one_standing"):
		return

	since = add_to_date(nowdate(), days=-90)
	for employee in frappe.get_all("Employee", filters={"status": "Active"}, pluck="name"):
		scores = frappe.get_all(
			"Clock Attempt",
			filters={"employee": employee, "creation": [">=", since]},
			pluck="score",
			order_by="creation asc",
		)
		frappe.db.set_value(
			"Employee",
			employee,
			{"one_standing": rules.standing(scores), "one_standing_on": now_datetime()},
			update_modified=False,
		)


def networks() -> None:
	"""An address several corroborated people arrived on becomes a proposal.

	Corroborated means the *place* gate passed on that same attempt: they were
	inside a fence while arriving from an address nobody had declared. That is
	the office's line having changed, and it is the one reading of it that
	somebody sitting in a café cannot produce.
	"""
	for address, votes, voters, place in _seen(corroborated="zone"):
		_learn(
			"Clock Network",
			{"address": ["in", [address, f"{address}/32"]]},
			{"address": address, "shift_location": place},
			votes,
			voters,
		)


def zones() -> None:
	"""Positions that cluster outside every circle become a second circle.

	A second rather than a wider one: stretching a radius to cover the car park
	also covers the road, and the road is where somebody sits in a car and
	clocks in.
	"""
	rows = frappe.get_all(
		"Clock Attempt",
		filters={
			"creation": [">=", add_to_date(nowdate(), days=-WINDOW_DAYS)],
			"zone": ["is", "not set"],
			"latitude": ["!=", 0],
			"network": ["is", "set"],
		},
		fields=["employee", "latitude", "longitude", "accuracy"],
	)
	for centre, votes, voters in _clusters(_with_standing(rows)):
		_learn(
			"Clock Place",
			{
				"latitude": ["between", [centre[0] - 0.001, centre[0] + 0.001]],
				"longitude": ["between", [centre[1] - 0.001, centre[1] + 0.001]],
			},
			{"latitude": centre[0], "longitude": centre[1], "radius": CLUSTER_METRES * 2},
			votes,
			voters,
		)


def forget_photos() -> None:
	"""The retention setting, applied. A face is personal data everywhere."""
	days = policy.get("one_keep_photo_days")
	if not days:
		return
	old = frappe.get_all(
		"Clock Attempt",
		filters={"photo": ["is", "set"], "creation": ["<", add_to_date(nowdate(), days=-int(days))]},
		fields=["name", "photo"],
	)
	for row in old:
		for file in frappe.get_all("File", filters={"file_url": row.photo}, pluck="name"):
			frappe.delete_doc("File", file, force=1, ignore_permissions=True)
		frappe.db.set_value("Clock Attempt", row.name, "photo", None, update_modified=False)


def _seen(corroborated: str):
	"""Addresses nobody declared, from attempts another gate vouched for."""
	rows = frappe.get_all(
		"Clock Attempt",
		filters={
			"creation": [">=", add_to_date(nowdate(), days=-WINDOW_DAYS)],
			"network": ["is", "not set"],
			corroborated: ["is", "set"],
			"address": ["is", "set"],
		},
		fields=["employee", "address", "zone"],
	)
	grouped: dict[str, dict] = {}
	for row in _with_standing(rows):
		one = grouped.setdefault(row["address"], {"votes": 0, "voters": set(), "place": None})
		one["votes"] += 1
		one["voters"].add(row["employee"])
		one["place"] = one["place"] or _place_of(row.get("zone"))

	for address, one in grouped.items():
		yield address, one["votes"], len(one["voters"]), one["place"]


def _with_standing(rows: list[dict]) -> list[dict]:
	"""Only the people whose word counts. A first week is not a witness."""
	if not frappe.db.has_column("Employee", "one_standing"):
		return rows
	standing = {
		row.name: row.one_standing
		for row in frappe.get_all("Employee", fields=["name", "one_standing"])
	}
	return [row for row in rows if (standing.get(row["employee"]) or 0) >= rules.FLAG_BELOW]


def _clusters(rows: list[dict]):
	"""Positions grouped by being near each other, greedily.

	Greedy rather than anything statistical: the question is whether a lot of
	people stand in the same spot, and a first-come centre answers it in one
	pass over a week of rows.
	"""
	found: list[dict] = []
	for row in rows:
		for one in found:
			if rules.distance(row["latitude"], row["longitude"], *one["centre"]) <= CLUSTER_METRES:
				one["votes"] += 1
				one["voters"].add(row["employee"])
				break
		else:
			found.append(
				{
					"centre": (row["latitude"], row["longitude"]),
					"votes": 1,
					"voters": {row["employee"]},
				}
			)

	for one in found:
		yield one["centre"], one["votes"], len(one["voters"])


def _learn(doctype: str, matching: dict, fields: dict, votes: int, voters: int) -> None:
	"""Proposed on the first corroborated sighting, Confirmed once enough agree.

	Two states rather than one so HR sees a thing being learned before it does
	anything, and so a rejection sticks: a Rejected row is matched here like any
	other and never promoted again.
	"""
	found = frappe.get_all(doctype, filters=matching, fields=["name", "status"], limit=1)
	threshold = int(policy.get("one_learn_threshold") or 3)
	agreed = rules.enough(votes, voters, threshold)

	if not found:
		doc = frappe.new_doc(doctype)
		doc.update(
			{
				**fields,
				"label": frappe._("Learned from {0} people").format(voters),
				"status": "Confirmed" if agreed else "Proposed",
				"first_seen": now_datetime(),
				"last_seen": now_datetime(),
				"attempts": votes,
				"voters": voters,
			}
		)
		doc.insert(ignore_permissions=True)
		if agreed:
			_tell(doc)
		return

	row = found[0]
	if row.status in ("Rejected", "Declared"):
		return

	frappe.db.set_value(
		doctype,
		row.name,
		{
			"last_seen": now_datetime(),
			"attempts": votes,
			"voters": voters,
			"status": "Confirmed" if agreed else row.status,
		},
		update_modified=False,
	)
	if agreed and row.status != "Confirmed":
		_tell(frappe.get_doc(doctype, row.name))


def _place_of(zone: str | None) -> str | None:
	return frappe.db.get_value("Clock Place", zone, "shift_location") if zone else None


def _tell(doc) -> None:
	"""One notification, to the people who can undo it.

	Told rather than asked: the row is already Confirmed and already working, on
	the reasoning that a Monday morning where nobody can clock in is worse than
	a place on the list that HR can reject at nine. A change nobody was told
	about is what makes a self-healing system feel haunted, so it is told.
	"""
	for user in frappe.get_all(
		"Has Role",
		filters={"role": "HR Manager", "parenttype": "User"},
		pluck="parent",
		distinct=True,
	):
		frappe.get_doc(
			{
				"doctype": "Notification Log",
				"for_user": user,
				"type": "Alert",
				"document_type": doc.doctype,
				"document_name": doc.name,
				"subject": frappe._("One learned a new place people clock in from"),
			}
		).insert(ignore_permissions=True)
