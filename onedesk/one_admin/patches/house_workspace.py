"""Four Degree Labs' own workspace, and the admin site linked to it
(house.ensure). On an admin site only; a customer's site has no Tenants."""

from onedesk.one_admin import house, site


def execute():
	if site.is_admin():
		house.ensure()
