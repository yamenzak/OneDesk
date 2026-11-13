"""What the workspace's account last said, as a connected workspace keeps it
(one/account.py's refresh writes the same fields): a Business plan, its
seats, storage and database, one storage add-on, credits, and its
addresses: the one One gave, its own made the main one, and one waiting on
its DNS record. A demo has no account to ask, so Plan and Credits and
Domains show this as what was last known, and invoices, the ledger and every
change as needing the account."""

import frappe
from frappe.utils import add_days, get_last_day, now_datetime, today

from onedesk.one_demo.base import COMPANY
from onedesk.one_demo.people import OWNER

GB = 1000**3

GIVEN = "saharaglass.t.4dl.app"


def run(password=None):
	held = frappe.get_single("Workspace Account")
	held.update(
		{
			"workspace_name": COMPANY,
			"plan": "Business",
			"plan_key": "business",
			"monthly": 240,
			"plan_currency": "USD",
			"seats": 15,
			"storage_bytes": int(18.4 * GB),
			"storage_limit": 75 * GB,
			"database_bytes": int(1.2 * GB),
			"database_limit": 5 * GB,
			"credits_balance": 4200,
			"credits_held": 0,
			"credits_month": 830,
			"credits_expiring": 1000,
			"credits_expires_on": get_last_day(today()),
			"billed_to": OWNER,
			"last_heard": add_days(now_datetime(), -1),
		}
	)
	held.set("add_ons", [{"offering": "storage_25", "label": "Extra Storage, 25 GB", "quantity": 1, "amount": 10}])
	held.dns_target = GIVEN
	held.set(
		"domains",
		[
			{"domain": GIVEN, "status": "Active", "given": 1},
			{"domain": "erp.saharaglass.com", "status": "Active", "primary": 1},
			{"domain": "portal.saharaglass.com", "status": "Pending"},
		],
	)
	held.flags.ignore_permissions = True
	held.save()
