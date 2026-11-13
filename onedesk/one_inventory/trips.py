"""A delivery trip, as OneInventory keeps it: ERPNext's own, with its route
buttons shown only where they can work."""

import frappe


def onload(doc, method=None) -> None:
	"""ERPNext works out arrival times and the best route with Google Maps,
	and without a key in Google Settings either button only says it cannot.
	The form is told whether there is one (public/js/one_inventory/delivery_trip.js)."""
	doc.set_onload("maps", bool(frappe.db.get_single_value("Google Settings", "api_key")))
