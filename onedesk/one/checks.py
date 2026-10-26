"""One's part of the integration suite (one_demo/check.py runs it): its
roles, and the Recycle Bin's Everyone's Deletions."""

import frappe

from onedesk.one_demo.base import as_user
from onedesk.one_demo.check import check
from onedesk.one_demo.people import OWNER


@check
def one_manager_sees_what_anybody_deleted():
	"""One's roles are made from its abilities.py (rights.settle) and its User
	role is everybody's. Nadia sees only what she deleted herself; given One
	Manager, which holds Everyone's Deletions, she sees what others deleted
	too, and still can't empty the bin for good."""
	from onedesk.one import recycle

	assert frappe.db.exists("Role", "One User") and frappe.db.exists("Role", "One Manager")
	assert "One User" in frappe.get_roles("nadia@one.test")
	others = frappe.db.get_value(
		"Deleted Document", {"owner": ("not in", ("nadia@one.test", "Administrator", "Guest"))}, "name"
	)
	assert others, "the demo has nothing deleted by anybody but Nadia"
	with as_user("nadia@one.test"):
		assert "nadia@one.test" in (recycle.query() or "") and not recycle._everyone("nadia@one.test")
	user = frappe.get_doc("User", "nadia@one.test")
	user.add_roles("One Manager")
	try:
		with as_user("nadia@one.test"):
			assert recycle._everyone("nadia@one.test"), "One Manager does not hold Everyone's Deletions"
			doc = frappe.get_doc("Deleted Document", others)
			assert recycle.has_permission(
				doc, "read", "nadia@one.test"
			) or doc.deleted_doctype not in recycle._kinds("nadia@one.test")
			assert not recycle.has_permission(doc, "delete", "nadia@one.test"), (
				"only an administrator empties the bin"
			)
	finally:
		user.remove_roles("One Manager")


@check
def the_bin_shows_what_was_deleted_by_day_and_puts_it_back():
	"""Nadia deletes a note; the bin's island lists it under Deleted, finds it
	by its words, and Put Back brings it back under Put Back. She sees only
	what she deleted, and is offered no Everyone's."""
	from onedesk.one import recycle

	with as_user("nadia@one.test"):
		note = frappe.get_doc(
			{"doctype": "ToDo", "description": "Bin check: call the glass supplier"}
		).insert()
		frappe.delete_doc("ToDo", note.name)
		ours = lambda rows: next((one for one in rows if one["title"] in (note.name, note.description)), None)  # noqa: E731
		said = recycle.read(kind="ToDo")
		assert not said["everyone"], "Nadia is offered everyone's deletions"
		row = ours(said["rows"])
		assert row and row["mine"] and row["kind"], said["rows"]
		assert said["counts"]["deleted"] >= 1 and any(one["doctype"] == "ToDo" for one in said["kinds"])
		assert all(one["mine"] for one in recycle.read(whose="everyone")["rows"]), (
			"Nadia sees somebody else's deletion"
		)
		got = recycle.bulk_restore([row["name"]])
		assert got["restored"] == [row["name"]], got
		back = ours(recycle.read(state="restored", kind="ToDo")["rows"])
		assert back and back["new_name"] and back["back_on"] >= back["on"], back
		frappe.delete_doc("ToDo", back["new_name"])


@check
def announcements_show_now_and_earlier_and_who_saw_them():
	"""Layla posts an announcement: it is under Showing Now for Samir, who
	sees no one's name and cannot stop it; Layla sees who has seen it, stops
	it, and it moves to Earlier."""
	from onedesk.one import announcements

	with as_user(OWNER):
		note = frappe.get_doc(
			{
				"doctype": "Note",
				"title": "Check: lift out of service",
				"content": "<p>Use the stairs.</p>",
				"public": 1,
				"notify_on_login": 1,
			}
		).insert()
	with as_user("samir@one.test"):
		said = announcements.read()
		row = next(one for one in said["rows"] if one["name"] == note.name)
		assert row["running"] and row["seen"] is None and not said["posts"], row
		assert "Use the stairs." in row["html"]
		try:
			announcements.stop(note.name)
			raise AssertionError("Samir stopped an announcement")
		except frappe.PermissionError:
			frappe.clear_last_message()
	with as_user(OWNER):
		said = announcements.read()
		assert said["posts"] and said["people"] > 1
		assert isinstance(next(one for one in said["rows"] if one["name"] == note.name)["seen"], list)
		announcements.stop(note.name)
		row = next(one for one in announcements.read()["rows"] if one["name"] == note.name)
		assert not row["running"] and row["ended"], row
		frappe.delete_doc("Note", note.name)


@check
def dashboards_are_under_the_app_they_are_about_for_who_works_in_it():
	"""Mariam, who works in OneHR, reads OneHR's dashboards and no other app's;
	Layla, who administers, reads every app's, Attendance under OneHR; a
	dashboard with nothing in it is nobody's to read."""
	from onedesk.one import dashboards

	with as_user("mariam@one.test"):
		hers = dashboards.read()["rows"]
		assert hers and {one["app"] for one in hers} <= {"OneHR", dashboards.HERE}, hers
		assert any(one["name"] == "Human Resource" for one in hers)
	with as_user(OWNER):
		said = dashboards.read()["rows"]
		apps = {one["app"] for one in said}
		assert {"OneHR", "OneCRM", "OneBook", "OneInventory"} <= apps, apps
		assert next(one["app"] for one in said if one["name"] == "Attendance") == "OneHR"
		assert all(one["charts"] or one["cards"] for one in said)


@check
def the_address_book_shows_a_person_with_their_places_and_a_place_with_its_people():
	"""Acme Holdings' billing address is in the Address Book with Acme as who
	it belongs to, and Jordan Blake, Acme's contact, beside it; opened from
	Jordan, the same address is among their places. A search narrows the
	list."""
	from onedesk.one import address_book

	with as_user(OWNER):
		place = next(one for one in address_book.read("addresses", "Acme")["rows"] if one["links"])
		assert {"doctype": "Customer", "name": "Acme Holdings", "title": "Acme Holdings"} in place["links"], (
			place
		)
		there = address_book.one("addresses", place["name"])
		assert "91 Park Avenue" in there["text"] and there["people"], there
		person = there["people"][0]
		theirs = address_book.one("contacts", person["name"])
		assert any(one["name"] == place["name"] for one in theirs["places"]), theirs["places"]
		assert all(
			"Acme" in (one["title"] + one["sub"]) for one in address_book.read("addresses", "Acme")["rows"]
		)
