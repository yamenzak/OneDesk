"""A weather source names a Weather Place now, where it held its own
coordinates (one/weather.py): each place a source held becomes a Weather
Place, one per name, and the first is the workspace's."""

import frappe


def execute():
	columns = set(frappe.db.get_table_columns("Display Source"))
	if not {"latitude", "longitude"} <= columns:
		return
	rows = frappe.db.sql(
		"""select name, place, latitude, longitude, units from `tabDisplay Source`
		where kind = 'Weather' and ifnull(weather_place, '') = ''""",
		as_dict=True,
	)
	for row in rows:
		named = (row.place or "").strip() or "Weather"
		if not frappe.db.exists("Weather Place", named):
			frappe.get_doc(
				{
					"doctype": "Weather Place",
					"place_name": named,
					"latitude": row.latitude,
					"longitude": row.longitude,
					"units": row.units or "Metric",
					"is_default": 0 if frappe.db.exists("Weather Place", {"is_default": 1}) else 1,
				}
			).insert(ignore_permissions=True)
		frappe.db.set_value("Display Source", row.name, "weather_place", named, update_modified=False)
