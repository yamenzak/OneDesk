"""Users, employees, the company and manufacturers made before they were
dressed get a picture, in the background (one_mail/faces.py)."""

import frappe


def execute():
	frappe.enqueue("onedesk.one_mail.faces.dress_all", queue="long", job_id="one_dress_all", deduplicate=True)
