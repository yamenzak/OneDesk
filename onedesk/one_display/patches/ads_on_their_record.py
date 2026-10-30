"""A voice ad's recording is a file on the ad now (D7), so OneCloud shows it
under Records › Voice Ad; one recorded before was filed on the Display Voice
it was kept as. Nothing sounds different."""

import frappe


def execute():
	for ad, url in frappe.get_all("Voice Ad", filters={"audio": ["is", "set"]}, fields=["name", "audio"], as_list=True):
		for name in frappe.get_all("File", filters={"file_url": url, "attached_to_doctype": "Display Voice"}, pluck="name"):
			frappe.db.set_value("File", name, {"attached_to_doctype": "Voice Ad", "attached_to_name": ad, "attached_to_field": "audio"}, update_modified=False)
