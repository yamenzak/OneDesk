"""Records made before pictures were looked for get one, in the background:
a migrate must not wait on Gravatar and Google (one_mail/faces.py)."""

import frappe


def execute():
	frappe.enqueue("onedesk.one_mail.faces.dress_all", queue="long", job_id="one_dress_all", deduplicate=True)
