from frappe import _


def get_data():
	return {
		"fieldname": "zone",
		"transactions": [{"label": _("Clock"), "items": ["Clock Attempt"]}],
	}
