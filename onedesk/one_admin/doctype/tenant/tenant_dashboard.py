"""The records that link back to a workspace.

Its jobs and its log, the domains it asked for, and on the billing side the
customer it is in our own books and the signup that paid for it.
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
