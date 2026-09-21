from frappe import _


def get_data():
	# What this address did, which is why somebody opens a proposal.
	return {
		"fieldname": "network",
		"transactions": [{"label": _("Clock"), "items": ["Clock Attempt"]}],
	}
