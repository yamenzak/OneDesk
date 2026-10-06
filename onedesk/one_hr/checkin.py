"""One override on HRMS's `Employee Checkin`, and the reason for it."""

import frappe
from frappe import _
from hrms.hr.doctype.employee_checkin.employee_checkin import (
	CheckinRadiusExceededError,
	EmployeeCheckin,
)

from onedesk.one_hr import gates, rules


class OneEmployeeCheckin(EmployeeCheckin):
	def validate_distance_from_shift_location(self):
		# A row from `clock.py` has been through One's own gates, whose network-or-place
		# setting a second radius check would overrule. Every other way in is checked below.
		if self.flags.get("one_gated"):
			return

		if not frappe.db.get_single_value("HR Settings", "allow_geolocation_tracking"):
			return

		if not (self.latitude or self.longitude):
			frappe.throw(_("Latitude and longitude values are required for checking in."))

		places = gates.places_of(self.employee)
		zones = [z for z in gates._zones(self.employee, places) if z.get("radius")]
		if not zones:
			return

		if rules.within(self.latitude, self.longitude, zones):
			return

		# Somewhere with no fence at all is a place people work at rather than a
		# place they have to stand in, so the distance is recorded and that is
		# the whole of the rule.
		if all(zone.get("is_site") for zone in zones):
			return

		nearest = min(
			rules.distance(self.latitude, self.longitude, zone["latitude"], zone["longitude"])
			for zone in zones
		)
		frappe.throw(
			_("You are {0} metres from the nearest location you may check in from.").format(
				int(nearest)
			),
			exc=CheckinRadiusExceededError,
		)
