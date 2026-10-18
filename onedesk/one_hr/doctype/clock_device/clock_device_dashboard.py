from frappe import _


def get_data():
	return {
		"fieldname": "device",
		"transactions": [{"label": _("Clock"), "items": ["Clock Attempt"]}],
	}
