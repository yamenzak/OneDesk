"""ERPNext's project page (/projects?project=…), as One's: it leads to the
project's page in the portal app (one_project/portal.py `page`). A redirect
rule can't, since frappe keeps a redirect by the path alone."""

from urllib.parse import quote

import frappe

no_cache = 1


def get_context(context):
	project = frappe.form_dict.get("project")
	frappe.local.flags.redirect_location = (
		f"/portal/projects/{quote(project)}" if project else "/portal/projects"
	)
	raise frappe.Redirect
