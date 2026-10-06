"""What OneAI reads for the company: the owner's own address, and the folder
the accounts team drops bank statements into. The samples in
tests/samples/intake arrive at these (samples.py)."""

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


def mailbox() -> str | None:
	from onedesk.one_mail import addresses

	return frappe.db.get_value("Email Account", {"email_id": addresses.person_address(ADDRESS)})


def folder() -> str | None:
	from onedesk.one_storage import namespace as ns

	return frappe.db.get_value("File", {"folder": ns.home(ACCOUNTS, create=False), "file_name": FOLDER, "is_folder": 1})
