"""One's part of the integration suite (one_demo/check.py runs it): its
roles, the Recycle Bin's Everyone's Deletions, and drawn pictures."""

import frappe

from onedesk.one_demo.base import as_user
from onedesk.one_demo.check import check
from onedesk.one_demo.people import OWNER


@check
def one_manager_sees_what_anybody_deleted():
	"""One's roles are made from its abilities.py (rights.settle) and its User
	role is everybody's. Nadia sees only what she deleted herself; made One's
	Manager in AccessCenter, which holds Everyone's Deletions, she sees what
	others deleted too, and still can't empty the bin for good. The demo keeps
	Mariam as One's Manager."""
	from onedesk.one import access_center, recycle

	assert frappe.db.exists("Role", "One User") and frappe.db.exists("Role", "One Manager")
	assert "One User" in frappe.get_roles("nadia@one.test")
	others = frappe.db.get_value(
		"Deleted Document", {"owner": ("not in", ("nadia@one.test", "Administrator", "Guest"))}, "name"
	)
	assert others, "the demo has nothing deleted by anybody but Nadia"
	with as_user("nadia@one.test"):
		assert "nadia@one.test" in (recycle.query() or "") and not recycle._everyone("nadia@one.test")
	assert "One" in access_center.modules() and "OneAccount" in access_center.modules()
	levels = {one["user"]: one["level"] for one in access_center.people("One")["people"]}
	assert levels.get("mariam@one.test") == "Manager" and levels.get("nadia@one.test") == "User", levels
	access_center.put("One", "nadia@one.test", "Manager")
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
		access_center.put("One", "nadia@one.test", "User")
		assert "One User" in frappe.get_roles("nadia@one.test") and "One Manager" not in frappe.get_roles("nadia@one.test")


@check
def the_bin_lists_what_was_deleted_and_puts_it_back():
	"""Nadia deletes a to-do; frappe's Deleted Document list, the Recycle Bin,
	shows it to her and nobody else's, and Restore (recycle.bulk_restore)
	brings it back, marking the row restored."""
	from onedesk.one import recycle

	with as_user("nadia@one.test"):
		note = frappe.get_doc({"doctype": "ToDo", "description": "Bin check: call the glass supplier"}).insert()
		frappe.delete_doc("ToDo", note.name)
		rows = frappe.get_list(
			"Deleted Document",
			filters={"deleted_doctype": "ToDo", "restored": 0},
			fields=["name", "deleted_name", "owner"],
			limit=500,
		)
		row = next((one for one in rows if one.deleted_name == note.name), None)
		assert row, rows
		assert not recycle._everyone("nadia@one.test")
		assert all(one.owner == "nadia@one.test" for one in rows), "Nadia sees somebody else's deletion"
		got = recycle.bulk_restore([row.name])
		assert got["restored"] == [row.name], got
		back = frappe.db.get_value("Deleted Document", row.name, ["restored", "new_name"], as_dict=True)
		assert back.restored and back.new_name, back
		frappe.delete_doc("ToDo", back.new_name)


@check
def announcements_show_now_and_earlier_and_who_saw_them():
	"""Layla posts an announcement with no end: it is given one a week out, so
	it is under Showing Now (Note's list, Show Until after now) for Samir, who
	cannot stop it; Layla stops it and it is under Earlier."""
	from frappe.utils import now_datetime

	from onedesk.one import announcements

	with as_user(OWNER):
		note = frappe.get_doc(
			{"doctype": "Note", "title": "Check: lift out of service", "content": "<p>Use the stairs.</p>", "public": 1}
		).insert()
		assert note.expire_notification_on and not note.notify_on_login, note.as_dict()
	shown = lambda op: frappe.get_list(  # noqa: E731
		"Note", filters={"public": 1, "expire_notification_on": [op, now_datetime()]}, pluck="name"
	)
	with as_user("samir@one.test"):
		assert note.name in shown(">") and note.name not in shown("<=")
		try:
			announcements.stop(note.name)
			raise AssertionError("Samir stopped an announcement")
		except frappe.PermissionError:
			frappe.clear_last_message()
	with as_user(OWNER):
		announcements.stop(note.name)
		assert note.name in shown("<=") and note.name not in shown(">")
		frappe.delete_doc("Note", note.name)


@check
def the_address_book_is_frappes_contacts_and_addresses():
	"""The rail's Contacts and Addresses are frappe's Contact and Address
	lists, and Acme Holdings' billing address and Jordan Blake both belong to
	Acme under Links."""
	rail = {one.label: one for one in frappe.get_all("Sidebar Item", filters={"parent": "One", "parenttype": "Sidebar"}, fields=["label", "link_type", "link_to"])}
	assert (rail["Contacts"].link_type, rail["Contacts"].link_to) == ("DocType", "Contact"), rail["Contacts"]
	assert (rail["Addresses"].link_type, rail["Addresses"].link_to) == ("DocType", "Address"), rail["Addresses"]
	with as_user(OWNER):
		for doctype in ("Address", "Contact"):
			linked = frappe.get_list(
				doctype,
				filters=[["Dynamic Link", "link_doctype", "=", "Customer"], ["Dynamic Link", "link_name", "=", "Acme Holdings"]],
				pluck="name",
			)
			assert linked, doctype


@check
def ones_rail_leaves_out_what_the_reader_cannot_open():
	"""One's rail links the workspace's centres by address, which frappe
	shows to everyone (reach.unopened): Mariam, who administers nothing, has
	AccountCenter and not ControlCenter or AccessCenter; Layla has them all."""
	from frappe.boot import get_module_sidebars

	from onedesk.one import reach

	def rail(user):
		with as_user(user):
			sidebars = get_module_sidebars()
			reach.unopened(sidebars)
			return [one.get("label") for one in sidebars["One"]["items"]]

	mariam, layla = rail("mariam@one.test"), rail(OWNER)
	assert "AccountCenter" in mariam and not {"ControlCenter", "AccessCenter"} & set(mariam), mariam
	assert {"AccountCenter", "ControlCenter", "AccessCenter", "TrustCenter"} <= set(layla), layla


@check
def a_record_with_no_picture_gets_one_drawn_and_keeps_its_own():
	"""A style picked for contacts in One's settings (avatars.save) draws a
	picture for a new contact with none, locally; one with its own picture
	keeps it; changing the style redraws only the drawn one, and None takes
	it off. The workspace's own choice is put back after."""
	from onedesk.one import avatars
	from onedesk.one_mail import faces

	before = frappe.db.get_default(avatars.KEY)
	keys = {one["key"] for one in avatars.styles()}
	assert {"lorelei", "shapes", "initials"} <= keys, sorted(keys)
	assert set(avatars.gallery("Contact")) == keys
	plain = frappe.get_doc({"doctype": "Contact", "first_name": "Drawn", "last_name": "Check"}).insert(ignore_permissions=True)
	own = frappe.get_doc(
		{"doctype": "Contact", "first_name": "Own", "last_name": "Picture", "image": "/files/own-picture.png"}
	).insert(ignore_permissions=True)
	try:
		frappe.db.set_default(avatars.KEY, '{"Contact": "lorelei"}')
		drawn = faces.dress("Contact", plain.name)
		assert drawn and avatars.style_of(drawn) == "lorelei", drawn
		assert "<metadata" in open(frappe.get_site_path("public", drawn.lstrip("/")), encoding="utf-8").read(), "no credit in the picture"
		assert not faces.dress("Contact", own.name)
		avatars.pick("Contact", "initials")
		avatars.fill("Contact")
		assert avatars.style_of(frappe.db.get_value("Contact", plain.name, "image")) == "initials"
		assert frappe.db.get_value("Contact", own.name, "image") == "/files/own-picture.png"
		frappe.db.set_default(avatars.KEY, "{}")
		avatars.fill("Contact")
		assert not frappe.db.get_value("Contact", plain.name, "image")
		assert frappe.db.get_value("Contact", own.name, "image") == "/files/own-picture.png"
	finally:
		frappe.db.set_default(avatars.KEY, before or "{}")
		for name in (plain.name, own.name):
			frappe.delete_doc("Contact", name, ignore_permissions=True, force=True)
		avatars.fill("Contact")
