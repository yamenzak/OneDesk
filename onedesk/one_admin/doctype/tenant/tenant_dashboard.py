"""The records that link back to a workspace.

Four, each its own list: the jobs that built or moved it, the domains it asked
for, the log of every status it reached, and the signup that paid for it. They
are connections rather than tabs of fields because they are lists that grow, and
each is a screen somebody opens on its own.

The group labels follow frappe's own — plain nouns, no narration. See
`tests/test_console.py`.
"""


def get_data():
	return {
		"fieldname": "tenant",
		"transactions": [
			{"label": "Activity", "items": ["Provisioning Job", "Tenant Event"]},
			{"label": "Domains", "items": ["Tenant Domain"]},
			{"label": "Billing", "items": ["Account Request"]},
		],
	}
