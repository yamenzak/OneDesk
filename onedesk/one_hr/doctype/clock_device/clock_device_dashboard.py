from frappe import _


def get_data():
	# Named rather than left to the doctype's own `links`, which frappe draws as
	# an unlabelled box above the connections.
	return {
		"fieldname": "device",
		"transactions": [{"label": _("Clock"), "items": ["Clock Attempt"]}],
	}
