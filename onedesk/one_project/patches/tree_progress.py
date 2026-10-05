"""A project with sub-projects stores its tree's progress as its % Complete
(overview.roll_up), so its page and the lists say the same. Set once here for
the projects that had sub-projects already."""

import frappe

from onedesk.one_project import overview, tree


def execute():
	down = tree.children(tree.parents())
	for project in down:
		if frappe.db.exists("Project", project):
			overview.roll_up(project)
