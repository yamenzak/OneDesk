"""What OneAI reads for the company: the owner's own address, and the folder
the accounts team drops bank statements into. The samples in
tests/samples/intake arrive at these and stay, as Intake left them
(samples.py)."""

import frappe

from onedesk.one_demo.base import as_user
from onedesk.one_demo.people import OWNER

#: The owner's address on the mail domain, `layla.<workspace>@`.
ADDRESS = "layla"
#: Where the books' bank statements go, in Huda's own files.
FOLDER = "Bank Statements"
ACCOUNTS = "huda@one.test"


def run(password=None):
	from onedesk.one_intake import switches
	from onedesk.one_mail import addresses
	from onedesk.one_storage import api
	from onedesk.one_storage import namespace as ns

	with as_user(OWNER):
		account = mailbox() or addresses.give(OWNER, ADDRESS)
		switches.set_mailbox(account, 1)
	with as_user(ACCOUNTS):
		found = folder()
		if not found:
			found = api.make_folder(ns.home(ACCOUNTS), FOLDER)["id"]
		switches.set_folder(found, 1)
	frappe.db.commit()
	rules()
	_samples()


#: The workspace shares tasks out by frappe's own Assignment Rules: what
#: Intake makes about a supplier is the books' work, whoever's mail it came in.
RULE = "Supplier Tasks to the Books"
DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def rules():
	if frappe.db.exists("Assignment Rule", RULE):
		return
	frappe.get_doc(
		{
			"doctype": "Assignment Rule",
			"name": RULE,
			"document_type": "Task",
			"description": "A task about a supplier goes to whoever keeps the books.",
			"assign_condition": 'one_about_doctype == "Supplier" and status == "Open"',
			"rule": "Round Robin",
			"users": [{"user": ACCOUNTS}],
			"assignment_days": [{"day": day} for day in DAYS],
		}
	).insert(ignore_permissions=True)


def _samples():
	"""Every sample arrives, in turn, and what Intake did with it is kept. One
	that does not make what it says stops the demo."""
	from onedesk.one_demo import samples

	for path in samples.samples():
		if samples.found(path):
			continue
		handled = samples.handle(path, kept=True)
		frappe.set_user("Administrator")
		missing = samples.unmet(path, handled)
		if missing:
			raise AssertionError(f"{path.parent.name}/{path.stem}: {missing}")
		frappe.db.commit()


def mailbox() -> str | None:
	from onedesk.one_mail import addresses

	return frappe.db.get_value("Email Account", {"email_id": addresses.person_address(ADDRESS)})


def folder() -> str | None:
	from onedesk.one_storage import namespace as ns

	return frappe.db.get_value("File", {"folder": ns.home(ACCOUNTS, create=False), "file_name": FOLDER, "is_folder": 1})
