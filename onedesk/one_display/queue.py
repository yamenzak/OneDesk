"""Queues: a ticket taken at a kiosk, called to a counter, and shown on the
board. Numbers start again each day, per service, from the service's prefix
(A001, B001). A counter calling the next ticket closes the one it was serving."""

from typing import Annotated

import frappe
from frappe import _
from frappe.utils import cint, now_datetime, today

DOCTYPE = "Queue Ticket"
BOARD = 8


def _service(queue: str, service: str) -> dict:
	found = next((row for row in frappe.get_cached_doc("Queue", queue).services if row.service == service), None)
	if not found:
		frappe.throw(_("{0} is not a service of {1}.").format(service, queue))
	return found


def _number(queue: str, prefix: str) -> int:
	"""The next number of the day for a prefix: counted in the cache so two
	kiosks never hand out the same one, started from the records."""
	key = frappe.cache.make_key(f"one_display_number:{queue}:{prefix}:{today()}")
	if not frappe.cache.exists(key):
		last = frappe.db.sql(
			"select max(number) from `tabQueue Ticket` where queue=%s and ticket_date=%s and ticket like %s",
			(queue, today(), f"{prefix}%"),
		)[0][0]
		frappe.cache.set(key, cint(last), ex=2 * 24 * 3600, nx=True)
	return int(frappe.cache.incrby(key, 1))


def take(queue: str, service: str) -> dict:
	"""A new ticket, as a kiosk prints it."""
	row = _service(queue, service)
	number = _number(queue, row.prefix)
	ticket = frappe.get_doc(
		{
			"doctype": DOCTYPE,
			"queue": queue,
			"service": service,
			"number": number,
			"ticket": f"{row.prefix}{number:03d}",
			"ticket_date": today(),
			"status": "Waiting",
		}
	).insert(ignore_permissions=True)
	ahead = frappe.db.count(DOCTYPE, {"queue": queue, "service": service, "ticket_date": today(), "status": "Waiting", "number": ["<", number]})
	return {"ticket": ticket.ticket, "service": service, "ahead": ahead}


def board(queue: str) -> dict:
	"""What a board shows: the tickets called today, newest first, and how many
	wait for each service."""
	called = frappe.get_all(
		DOCTYPE,
		filters={"queue": queue, "ticket_date": today(), "status": "Called"},
		fields=["name", "ticket", "counter", "called_at", "calls"],
		order_by="called_at desc",
		limit=BOARD,
	)
	waiting = frappe.get_all(
		DOCTYPE,
		filters={"queue": queue, "ticket_date": today(), "status": "Waiting"},
		fields=["service", {"COUNT": "*", "as": "waiting"}],
		group_by="service",
	)
	counts = {row.service: row.waiting for row in waiting}
	services = [
		{"service": row.service, "prefix": row.prefix, "waiting": counts.get(row.service, 0)}
		for row in frappe.get_cached_doc("Queue", queue).services
	]
	return {
		"called": [
			{"id": f"{row.name}:{row.calls}", "ticket": row.ticket, "counter": row.counter, "at": str(row.called_at)}
			for row in called
		],
		"services": services,
	}


def _may(queue: str) -> None:
	frappe.has_permission(DOCTYPE, "write", throw=True)
	frappe.has_permission("Queue", "read", doc=queue, throw=True)


def _serving(queue: str, counter: str) -> str | None:
	return frappe.db.get_value(
		DOCTYPE, {"queue": queue, "counter": counter, "status": "Called", "ticket_date": today()}, "name"
	)


@frappe.whitelist(methods=["POST"])
def call_next(
	queue: Annotated[str, "The queue."],
	counter: Annotated[str, "The counter calling."],
	service: Annotated[str | None, "Only this service's tickets."] = None,
) -> dict:
	"""Close what this counter was serving and call the longest waiting ticket."""
	_may(queue)
	serving = _serving(queue, counter)
	if serving:
		frappe.db.set_value(DOCTYPE, serving, "status", "Done")
	filters = {"queue": queue, "ticket_date": today(), "status": "Waiting"}
	if service:
		filters["service"] = service
	found = frappe.get_all(DOCTYPE, filters=filters, fields=["name"], order_by="creation asc", limit=1)
	if not found:
		return counter_state(queue, counter)
	_call(found[0].name, counter)
	return counter_state(queue, counter)


def _call(name: str, counter: str) -> None:
	ticket = frappe.get_doc(DOCTYPE, name)
	ticket.update(
		{
			"status": "Called",
			"counter": counter,
			"called_at": now_datetime(),
			"called_by": frappe.session.user,
			"calls": cint(ticket.calls) + 1,
		}
	)
	ticket.save(ignore_permissions=True)


@frappe.whitelist(methods=["POST"])
def recall(ticket: Annotated[str, "The ticket to call again."]) -> dict:
	"""Call the same ticket again, as the board announces it again."""
	doc = frappe.get_doc(DOCTYPE, ticket)
	_may(doc.queue)
	_call(ticket, doc.counter)
	return counter_state(doc.queue, doc.counter)


@frappe.whitelist(methods=["POST"])
def finish(
	ticket: Annotated[str, "The ticket."],
	status: Annotated[str, "Done or No Show."] = "Done",
) -> dict:
	"""The ticket is served, or nobody came."""
	if status not in ("Done", "No Show"):
		frappe.throw(_("A ticket is finished as Done or No Show."))
	doc = frappe.get_doc(DOCTYPE, ticket)
	_may(doc.queue)
	frappe.db.set_value(DOCTYPE, ticket, "status", status)
	return counter_state(doc.queue, doc.counter)


@frappe.whitelist()
def counter_state(queue: Annotated[str, "The queue."], counter: Annotated[str, "The counter."]) -> dict:
	"""What a counter's screen shows: the ticket it is serving and who waits."""
	frappe.has_permission("Queue", "read", doc=queue, throw=True)
	serving = _serving(queue, counter)
	return {
		"serving": frappe.db.get_value(DOCTYPE, serving, ["name", "ticket", "service", "calls"], as_dict=True) if serving else None,
		"waiting": frappe.get_all(
			DOCTYPE,
			filters={"queue": queue, "ticket_date": today(), "status": "Waiting"},
			fields=["name", "ticket", "service", "creation"],
			order_by="creation asc",
			limit=50,
		),
	}


@frappe.whitelist()
def desks() -> list[dict]:
	"""The queues the reader may work, each with its counters and the one the
	reader staffs."""
	said = []
	for name in frappe.get_list("Queue", pluck="name", order_by="name asc"):
		counters = frappe.get_cached_doc("Queue", name).counters
		said.append(
			{
				"queue": name,
				"counters": [row.counter for row in counters],
				"mine": next((row.counter for row in counters if row.user == frappe.session.user), None),
			}
		)
	return said
