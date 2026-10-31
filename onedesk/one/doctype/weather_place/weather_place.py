import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class WeatherPlace(Document):
	def validate(self):
		if not (-90 <= flt(self.latitude) <= 90 and -180 <= flt(self.longitude) <= 180):
			frappe.throw(_("A latitude is between -90 and 90, and a longitude between -180 and 180."))

	def on_update(self):
		# one place is the default: choosing this one lets the last go
		if self.is_default:
			frappe.db.set_value("Weather Place", {"is_default": 1, "name": ["!=", self.name]}, "is_default", 0)
		from onedesk.one import weather

		weather.forget(self.name)
