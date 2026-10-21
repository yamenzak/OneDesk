"""A scope of works in the company's files: what the Bayview tower quotation
covers, written as a document. Shared with Karim, so two people can work on
it at once. It is written as HTML, so it also shows a document made outside
the editor opening in it."""

import frappe

from onedesk.one_demo.base import as_user
from onedesk.one_doc import api

OWNER = "wsadmin@one.test"
CHECKER = "karim@one.test"
NAME = "bayview-scope"
TITLE = "Bayview tower scope of works"

HTML = """<h1>Bayview tower scope of works</h1>
<p>What the quotation for the Bayview tower facade covers, and what it leaves to others.</p>
<h2>Curtain wall</h2>
<ul>
<li>Unitised curtain wall on floors 2 to 18, 420 m² of double glazed units.</li>
<li>Aluminium mullions and transoms, powder coated to RAL 7016.</li>
<li>Structural silicone glazing and weather seals.</li>
</ul>
<h2>Not included</h2>
<p>Scaffolding, the tower crane after the first lift, and any work below ground floor.</p>
<h2>Programme</h2>
<p>Forty-five working days on site from the handover of the first floor.</p>"""


def run(password=None):
	if not frappe.db.exists(api.DOCUMENT, NAME):
		_make()
	file = frappe.db.get_value(api.DOCUMENT, NAME, "file")
	if frappe.db.exists("User", CHECKER) and not frappe.db.exists("DocShare", {"share_doctype": "File", "share_name": file, "user": CHECKER}):
		frappe.share.add_docshare("File", file, CHECKER, read=1, write=1, notify=0, flags={"ignore_share_permission": True})


def _make():
	from onedesk.one_storage import namespace as ns

	with as_user(OWNER):
		doc = frappe.get_doc({"doctype": api.DOCUMENT, "title": TITLE, "html": HTML})
		doc.flags.ignore_permissions = True
		doc.insert(set_name=NAME)
		file = frappe.get_doc({"doctype": "File", "file_url": api.URL + NAME, "is_private": 1, "folder": ns.HOME, "file_name": TITLE})
		file.flags.ignore_permissions = True
		file.insert()
		doc.db_set("file", file.name)
