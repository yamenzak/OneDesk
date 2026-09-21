"""One override on HRMS's `Employee Checkin`, and the reason for it.

`validate_distance_from_shift_location` collects **every** Shift Location
assigned to the employee for that shift — and then checks `[0]`. The list is
built and thrown away, so a company with a depot and four live sites can only
ever have one fence, and whichever row the database happened to return first is
the one everybody has to stand in.

So this subclass checks all of them and passes on any, adds the zones this app
lets a workspace draw, and treats a location marked as a site the way field work
needs: record how far out they were and let them through, because a system that
locks a plumber out at a customer's door is a system they stop using.

Nothing else is touched. The shift resolution, the duplicate window, the
geolocation requirement and the auto-attendance link are all still HRMS's, and
`docs/OVERRIDES.md` carries the line this depends on so an update that moves it
fails a test rather than a screen.
"""

import frappe
from frappe import _
from hrms.hr.doctype.employee_checkin.employee_checkin import (
	CheckinRadiusExceededError,
	EmployeeCheckin,
)

from onedesk.one_hr import gates, rules


class OneEmployeeCheckin(EmployeeCheckin):
	def validate_distance_from_shift_location(self):
		# A row written by `clock.py` has already been through One's own gates,
		# and those answer a question this one cannot: a workspace that says the
		# network *or* the place will do has said that being on the office line
		# settles it. Checking the radius again here would overrule that setting
		# from underneath it. Every other way a check-in is made — the desk
		# form, an import, HRMS's own app — still comes through below.
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
