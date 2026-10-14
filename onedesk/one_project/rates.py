"""Activity Type: what an hour of each activity costs and is billed at."""

from frappe import _


def dashboard(data: dict) -> dict:
	"""An activity's connections: its rates for each person."""
	data["fieldname"] = "activity_type"
	data["transactions"] = [{"label": _("Activity Cost"), "items": ["Activity Cost"]}]
	return data


def homes() -> dict[str, list[dict]]:
	"""`one_homes`: an Activity Cost leads back to Activity Type, where it is
	listed under its activity, and Projects Settings to the Projects list it is
	opened from."""
	return {
		"Activity Cost": [{"label": _("Activity Type"), "route": "/desk/activity-type"}],
		"Projects Settings": [{"label": _("Project"), "route": "/desk/project"}],
	}
