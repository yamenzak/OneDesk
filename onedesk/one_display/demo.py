"""The showroom's queue: a kiosk at the door hands out tickets for three
services, three counters call them, and the lobby screen shows who is called.
Layla runs OneDisplay and Omar works a counter, and the morning so far is
six tickets: some served, one nobody came for, one at a counter and two
waiting. The screens themselves are not made here: a screen is paired by
opening /tv on it."""

import frappe

from onedesk.one_demo.people import OWNER

QUEUE = "Showroom"
CHANNEL = "Showroom Lobby"
SERVICES = (("Showroom Visit", "A"), ("Collections", "B"), ("Payments", "C"))
COUNTERS = (("1", OWNER), ("2", "omar@one.test"), ("3", None))
ROLES = {OWNER: "OneDisplay Manager", "omar@one.test": "OneDisplay User"}


def run(password=None):
	if not frappe.db.exists("Queue", QUEUE):
		frappe.get_doc(
			{
				"doctype": "Queue",
				"queue_name": QUEUE,
				"services": [{"service": name, "prefix": prefix} for name, prefix in SERVICES],
				"counters": [{"counter": counter, "user": user} for counter, user in COUNTERS],
			}
		).insert(ignore_permissions=True)
	if not frappe.db.exists("Display Channel", CHANNEL):
		frappe.get_doc(
			{
				"doctype": "Display Channel",
				"channel_name": CHANNEL,
				"queue": QUEUE,
				"headline": "Now Serving",
				"announce": 1,
				"ticker": "Welcome to the Sahara Glass showroom. Take a ticket at the kiosk and we will call you shortly.",
			}
		).insert(ignore_permissions=True)
	_morning()
	for user, role in ROLES.items():
		if frappe.db.exists("User", user):
			doc = frappe.get_doc("User", user)
			doc.flags.ignore_permissions = True
			doc.add_roles(role)


# (service, counter that served it, how it ended)
MORNING = (
	("Showroom Visit", "1", "Done"),
	("Payments", "2", "Done"),
	("Collections", "2", "No Show"),
	("Showroom Visit", "1", "Called"),
	("Showroom Visit", None, "Waiting"),
	("Payments", None, "Waiting"),
)


def _morning():
	from onedesk.one_display import queue as queues

	if frappe.db.exists("Queue Ticket", {"queue": QUEUE}):
		return
	for service, counter, status in MORNING:
		ticket = queues.take(QUEUE, service)
		if not counter:
			continue
		name = frappe.db.get_value("Queue Ticket", {"queue": QUEUE, "ticket": ticket["ticket"], "status": "Waiting"})
		queues._call(name, counter)
		if status != "Called":
			frappe.db.set_value("Queue Ticket", name, "status", status)
