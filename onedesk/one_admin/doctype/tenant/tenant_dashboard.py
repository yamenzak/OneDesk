"""The records that link back to a workspace.

Its jobs and its log, the domains it asked for, and on the billing side the
customer it is in our own books and the signup that paid for it. They are
connections rather than tabs of fields because they are lists that grow, and
each is a screen somebody opens on its own.

Each is called what the rail calls it (`one/titles.py` renames our own
doctypes in the browser); the customer is erpnext's, and keeps its name. Its
invoices are one click from it, and from the form's Billing menu.
"""


def get_data():
	return {
		"fieldname": "tenant",
		"internal_links": {"Customer": "customer"},
		"transactions": [
			{"label": "Activity", "items": ["Provisioning Job", "Tenant Event"]},
			{"label": "Domains", "items": ["Tenant Domain"]},
			{"label": "Billing", "items": ["Customer", "Account Request"]},
		],
	}
