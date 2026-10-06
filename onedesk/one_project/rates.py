"""Rates: what an hour of each activity costs and is billed at."""

from frappe import _


def dashboard(data: dict) -> dict:
	"""An activity's connections: its rates for each person."""
	data["fieldname"] = "activity_type"
	data["transactions"] = [{"label": _("Rates for a Person"), "items": ["Activity Cost"]}]
	return data


def homes() -> dict[str, list[dict]]:
	"""`one_homes`: a person's rate leads back to Rates, where it is listed
	under its activity, and Projects Settings to the Projects list it is
	opened from."""
	return {
		"Activity Cost": [{"label": _("Rates"), "route": "/desk/activity-type"}],
		"Projects Settings": [{"label": _("Projects"), "route": "/desk/project"}],
	}
