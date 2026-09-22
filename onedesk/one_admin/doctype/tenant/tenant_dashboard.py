"""What else there is to read about a workspace.

Four things happened to it and each is its own record: the jobs that built or
moved it, the domains it asked for, the log of every rung it fell to, and the
signup that paid for it. They are here rather than as tabs of fields because
they are lists that grow, and because each one is a screen somebody opens on
its own when they are chasing a different question.
"""


def get_data():
	return {
		"fieldname": "tenant",
		"transactions": [
			{"label": "What happened", "items": ["Provisioning Job", "Tenant Event"]},
			{"label": "Where it is reached", "items": ["Tenant Domain"]},
			{"label": "What they bought", "items": ["Account Request"]},
		],
	}
