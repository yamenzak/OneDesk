"""A customer's page for one of their projects, at ERPNext's own address.

ERPNext's page here refused every customer and showed the team's assignments;
this one takes its place, since frappe renders the last app's page for a route.
See one_project/portal.py.
"""

import frappe

from onedesk.one_project import portal

no_cache = 1


def get_context(context):
	project = frappe.form_dict.get("project")
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = f"/login?redirect-to=/projects?project={project or ''}"
		raise frappe.Redirect
	if not project or not frappe.db.exists("Project", project):
		raise frappe.DoesNotExistError
	context.update(portal.view(project))
	context.when = portal.when(context.days_left)
	context.no_cache = 1
	context.show_sidebar = True
	context.title = context.doc.project_name
	context.parents = [{"route": "/project", "title": frappe._("Projects")}]
