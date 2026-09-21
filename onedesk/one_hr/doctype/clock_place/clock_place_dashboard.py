from frappe import _


def get_data():
	# Who checked in from inside this circle, and who was just outside it.
	return {
		"fieldname": "zone",
		"transactions": [{"label": _("Clock"), "items": ["Clock Attempt"]}],
	}
