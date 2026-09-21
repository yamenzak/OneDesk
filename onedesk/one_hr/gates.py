"""The three gates, each answering rather than throwing.

Nothing here refuses anybody. Each gate reports what it saw and which signals it
raised, `clock.py` adds them up, and the score decides. That split is what lets
the same code run in a workspace that enforces every gate and in one that only
watches, and it is why the ledger records the same fields either way.

The order they run in is about cost, not importance: the passkey first because
nothing else means anything without knowing who, then the network because it is
one string comparison with no prompt, then the place, which needs the
employee's permission and a second or two for a fix and should not be paid for
by somebody whose passkey already failed.
"""

import frappe
from frappe.utils import add_to_date, get_datetime, getdate

from onedesk.one_hr import ledger, passkey, policy, rules

#: How far back to look for another clock-in when asking whether the journey
#: between two of them was possible. A whole day is more than enough and keeps
#: the query on one index.
LOOK_BACK_HOURS = 24


def passkey_gate(employee: str, credential, seen: dict) -> dict:
	"""Who. The only gate whose failure is worth refusing on by itself."""
	if not policy.on("one_gate_passkey"):
		return {"signals": [], "device": None, "verified": 0}

	if not credential:
		return {"signals": ["no-passkey"], "device": None, "verified": 0}

	checked = passkey.check(credential, employee)
	signals = [checked["why"]] if checked["why"] else []

	held = passkey.held_by(employee)
	if checked["device"] and held and _unlike(held.get("user_agent"), seen.get("user_agent")):
		signals.append("passkey-elsewhere")

	if passkey.resets_since(employee, add_to_date(getdate(), days=-30)) > 1:
		signals.append("reset-recent")

	return {
		"signals": signals,
		"device": checked["device"],
		"verified": int(bool(checked["verified"])),
	}


def network_gate(employee: str, places: list[str]) -> dict:
	"""Whose network. One comparison, no prompt, and no header is trusted.

	`request_ip` is what Frappe resolved from the connection and the proxy
	headers it is configured to trust. Reading `X-Forwarded-For` here instead
	would be trusting a header the caller sets, which is the whole of the attack
	on this kind of rule.
	"""
	found = {"address": frappe.local.request_ip, "network": None, "signals": []}
	if not policy.on("one_gate_network"):
		return found

	seen = rules.address(found["address"])
	if not seen:
		found["signals"].append("network-unknown")
		return found

	for row in _known_networks(employee, places):
		if any(seen in one for one in rules.networks(row.address)):
			found["network"] = row.name
			if row.employee and not row.shift_location:
				# Their own home rather than a place the company holds. Worth a
				# point, because a home address is one person's word for it.
				found["signals"].append("network-personal")
			return found

	found["signals"].append("network-unknown")
	return found


def place_gate(employee: str, places: list[str], position: dict) -> dict:
	"""Where the browser says they are, against every zone that counts.

	Every one of them rather than the nearest, and rather than HRMS's first:
	a depot and four live sites all counting is the point of having them.
	"""
	found = {
		"latitude": None,
		"longitude": None,
		"accuracy": None,
		"zone": None,
		"metres_out": None,
		"position_state": "Absent",
		"signals": [],
	}
	if not policy.on("one_gate_place"):
		return found

	position = position or {}
	if position.get("refused"):
		found["position_state"] = "Refused"
		found["signals"].append("place-refused")
		return found

	lat, lon = position.get("latitude"), position.get("longitude")
	if lat in (None, "") or lon in (None, ""):
		found["signals"].append("place-absent")
		return found

	found.update(
		{
			"latitude": float(lat),
			"longitude": float(lon),
			"accuracy": float(position.get("accuracy") or 0),
			"position_state": "Given",
		}
	)

	zones = _zones(employee, places)
	if not zones:
		# Nowhere to be outside of. A workspace that has switched the gate on
		# but drawn no circles gets a position recorded and nothing refused.
		return found

	inside = rules.within(found["latitude"], found["longitude"], zones)
	if inside:
		found["zone"] = inside["name"]
		# A position good to two kilometres that lands inside a fifty metre
		# circle has not told us anything. A desktop with no GPS answers like
		# this, and so does a fake.
		if found["accuracy"] and found["accuracy"] > float(inside["radius"]):
			found["signals"].append("place-vague")
		return found

	nearest = min(
		rules.distance(found["latitude"], found["longitude"], z["latitude"], z["longitude"])
		- float(z["radius"])
		for z in zones
	)
	found["metres_out"] = round(max(0.0, nearest), 1)
	# A site records the distance and lets them through; a fence does not.
	if not all(z.get("is_site") for z in zones):
		found["signals"].append("place-outside")
	return found


def history_gate(employee: str, seen: dict, position: dict, when) -> dict:
	"""What the last day says about this attempt.

	Three questions the ledger can answer that no single gate can: could they
	have got here from where they last were, is anybody else clocking in from
	this same browser, and is their desk session live from somewhere else.
	"""
	signals = []
	since = add_to_date(when, hours=-LOOK_BACK_HOURS)

	before = [row for row in ledger.recent(employee, since) if row.get("latitude")]
	if before and position and position.get("latitude") not in (None, ""):
		last = before[-1]
		metres = rules.distance(
			float(position["latitude"]), float(position["longitude"]), last["latitude"], last["longitude"]
		)
		seconds = (get_datetime(when) - get_datetime(last["creation"])).total_seconds()
		if rules.impossible(metres, seconds):
			signals.append("travel-impossible")

	if ledger.others_on(seen, employee, add_to_date(when, hours=-12)):
		signals.append("device-shared")

	if ledger.same_second(when, employee):
		signals.append("same-second")

	session = _session_address()
	if session and frappe.local.request_ip and session != frappe.local.request_ip:
		signals.append("session-elsewhere")

	return {"signals": signals, "session_address": session}


def places_of(employee: str) -> list[str]:
	"""Every Shift Location this employee's shift may clock in from, today.

	HRMS collects exactly this list in `validate_distance_from_shift_location`
	and then checks `[0]`, which is the difference between one fence and a set.
	Ours keeps the list, and adds the child table of other places a location
	names — a depot plus every live site in one record, rather than four
	overlapping shift assignments.
	"""
	today = getdate()
	found = frappe.get_all(
		"Shift Assignment",
		filters={
			"employee": employee,
			"docstatus": 1,
			"status": "Active",
			"start_date": ["<=", today],
			"shift_location": ["is", "set"],
		},
		or_filters=[["end_date", ">=", today], ["end_date", "is", "not set"]],
		pluck="shift_location",
		ignore_permissions=True,
	)
	places = list(dict.fromkeys(found))
	for place in list(places):
		places.extend(_also_at(place))
	return list(dict.fromkeys(places))


def _also_at(place: str) -> list[str]:
	if not frappe.db.has_column("Shift Location", "one_also_at"):
		return []
	return frappe.get_all(
		"Shift Location Place",
		filters={"parent": place, "parenttype": "Shift Location"},
		pluck="shift_location",
		ignore_permissions=True,
	)


def _known_networks(employee: str, places: list[str]) -> list:
	return frappe.get_all(
		"Clock Network",
		filters={"status": ["in", ["Declared", "Confirmed"]]},
		or_filters=[
			["shift_location", "in", places or [""]],
			["employee", "=", employee],
			["shift_location", "is", "not set"],
		],
		fields=["name", "address", "employee", "shift_location"],
		ignore_permissions=True,
	)


def _zones(employee: str, places: list[str]) -> list[dict]:
	"""Every circle that counts: HRMS's own on each place, plus ours.

	The Shift Location's own coordinates and radius are a zone like any other,
	so a workspace that set them up in HRMS before this app existed keeps
	working with nothing to migrate.
	"""
	zones = []
	for place in places or []:
		row = frappe.db.get_value(
			"Shift Location",
			place,
			["name", "latitude", "longitude", "checkin_radius", "location_name"],
			as_dict=True,
		)
		if row and row.checkin_radius and (row.latitude or row.longitude):
			zones.append(
				{
					"name": None,
					"label": row.location_name,
					"latitude": row.latitude,
					"longitude": row.longitude,
					"radius": row.checkin_radius,
					"is_site": _is_site(place),
				}
			)

	ours = frappe.get_all(
		"Clock Place",
		filters={"status": ["in", ["Declared", "Confirmed"]]},
		or_filters=[["shift_location", "in", places or [""]], ["employee", "=", employee]],
		fields=["name", "label", "latitude", "longitude", "radius", "shift_location"],
		ignore_permissions=True,
	)
	for row in ours:
		zones.append({**row, "is_site": _is_site(row.get("shift_location"))})
	return zones


def _is_site(place: str | None) -> bool:
	if not place or not frappe.db.has_column("Shift Location", "one_is_site"):
		return False
	return bool(frappe.db.get_value("Shift Location", place, "one_is_site"))


def _session_address() -> str | None:
	"""Where this person's desk session is live from, when they have one.

	Frappe already records it and we do not have to ask anybody for it. A
	clock-in from the office while their only session is live from another
	country is worth knowing; it is never a clock in its own right.
	"""
	found = frappe.db.sql(
		"""select `ipaddress` from tabSessions where user = %s
		order by lastupdate desc limit 1""",
		frappe.session.user,
	)
	return found[0][0] if found and found[0][0] else None


def _unlike(was: str | None, now: str | None) -> bool:
	"""Whether two browsers look like different machines.

	Version numbers move every six weeks and would cry wolf every six weeks, so
	the comparison is the platform in brackets — the part that says iPhone or
	Windows — rather than the whole string.
	"""
	if not was or not now:
		return False
	return _bracketed(was) != _bracketed(now)


def _bracketed(agent: str) -> str:
	start, _, rest = agent.partition("(")
	return rest.partition(")")[0].strip().lower() if rest else agent.strip().lower()
