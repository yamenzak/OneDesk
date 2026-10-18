from frappe import _


def get_data():
	return {
		"fieldname": "network",
		"transactions": [{"label": _("Clock"), "items": ["Clock Attempt"]}],
	}
