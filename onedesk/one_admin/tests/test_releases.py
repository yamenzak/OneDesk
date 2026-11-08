"""Updates in the Saturday window, with each app at the commit the gates
passed (one_admin/releases.py)."""

from datetime import datetime

from onedesk.one_admin import releases


def test_the_window_is_the_first_saturday_at_least_three_days_away():
	assert releases.window_after(datetime(2026, 11, 8, 12, 0)) == datetime(2026, 11, 14, 1, 0), "Sunday noon: Saturday is six days off"
	assert releases.window_after(datetime(2026, 11, 12, 12, 0)) == datetime(2026, 11, 21, 1, 0), "Thursday noon: this Saturday is under three days off"
	assert releases.window_after(datetime(2026, 11, 11, 1, 0)) == datetime(2026, 11, 14, 1, 0), "exactly three days is enough"


def _app(name, current, releases_, next_release=None, update=True):
	return {"app": name, "current_hash": current, "releases": releases_, "next_release": next_release, "update_available": update, "source": f"SRC-{name}"}


def test_a_pinned_app_goes_to_its_pin_and_ours_to_main():
	apps = [
		_app("frappe", "aaa", [{"name": "r-new", "hash": "fff"}, {"name": "r-pin", "hash": "pin1234", "source": "SRC-frappe"}]),
		_app("onedesk", "old", [{"name": "r-main", "hash": "main99"}], next_release="r-main"),
		_app("hrms", "pin5678", [{"name": "r-h", "hash": "pin5678"}]),
	]
	chosen, missing = releases.chosen(apps, {"frappe": "pin1234", "hrms": "pin5678"})
	assert [(one["app"], one["release"]) for one in chosen] == [("frappe", "r-pin"), ("onedesk", "r-main")], "hrms is already on its pin"
	assert not missing


def test_a_pin_frappe_cloud_does_not_offer_holds_it():
	chosen, missing = releases.chosen([_app("erpnext", "x", [{"name": "r", "hash": "develop-head"}])], {"erpnext": "pinned"})
	assert chosen == [] and missing == ["erpnext"]
